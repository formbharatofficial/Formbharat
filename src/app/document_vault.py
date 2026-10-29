import os
import sqlite3
import hashlib
import json
import uuid
from datetime import datetime
from flask import jsonify, render_template_string, request, send_file
from app.document_ocr import extract_text
from app.profile import profile_exists

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(BASE_DIR, "formbharat.db")
# Files are stored as uploaded bytes. At-rest encryption is not enabled.
STORAGE_DIR = os.path.join(BASE_DIR, "documents")

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_DOC_TYPES = {
    "aadhaar",
    "pan",
    "10th",
    "12th",
    "graduation",
    "category",
    "domicile",
    "income",
    "photo",
    "signature",
    "other",
    "identity",
    "education",
}


def _documents_table_sql():
    return """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            doc_type TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            mime_type TEXT,
            file_hash TEXT,
            extracted_text TEXT,
            extracted_data TEXT,
            verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            document_version INTEGER NOT NULL DEFAULT 1,
            document_reference TEXT NOT NULL,
            processing_status TEXT NOT NULL DEFAULT 'processed',
            file_size INTEGER NOT NULL DEFAULT 0,
            capture_source TEXT NOT NULL DEFAULT 'file'
        )
    """


def _generate_document_reference(conn):
    while True:
        reference = f"DOC-{uuid.uuid4().hex.upper()}"
        existing = conn.execute(
            "SELECT 1 FROM documents WHERE document_reference = ?",
            (reference,)
        ).fetchone()
        if existing is None:
            return reference


def init_db():
    """Create the existing Document Vault schema when it is not present."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(_documents_table_sql())
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(documents)")
        }
        if "document_version" not in columns:
            conn.execute(
                "ALTER TABLE documents "
                "ADD COLUMN document_version INTEGER NOT NULL DEFAULT 1"
            )
        if "document_reference" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN document_reference TEXT"
            )
        if "processing_status" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN processing_status "
                "TEXT NOT NULL DEFAULT 'processed'"
            )
        if "file_size" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN file_size "
                "INTEGER NOT NULL DEFAULT 0"
            )
        if "capture_source" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN capture_source "
                "TEXT NOT NULL DEFAULT 'file'"
            )

        rows = conn.execute(
            "SELECT id, document_reference FROM documents ORDER BY id"
        ).fetchall()
        seen_references = set()
        for document_id, document_reference in rows:
            if document_reference and document_reference not in seen_references:
                seen_references.add(document_reference)
                continue

            document_reference = _generate_document_reference(conn)
            conn.execute(
                "UPDATE documents SET document_reference = ? WHERE id = ?",
                (document_reference, document_id)
            )
            seen_references.add(document_reference)

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_documents_document_reference
            ON documents(document_reference)
            """
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def verified_documents_for_profile(profile_id):
    """Return verified vault rows for one profile.

    Unverified documents and other profiles are not included.
    """
    init_db()
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, profile_id, doc_type, document_reference, verified
            FROM documents
            WHERE profile_id = ? AND verified = 1
            ORDER BY id DESC
            """,
            (profile_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _clear_verified_profile(conn, profile_id):
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "verified_profile" not in tables:
        return
    conn.execute(
        "UPDATE verified_profile SET verified = 0 WHERE profile_id = ?",
        (profile_id,),
    )


def _capture_source(value):
    source = str(value or "file").strip().lower()
    if source in {"file", "camera"}:
        return source
    return None


_FILE_SIGNATURES = {
    "pdf": b"%PDF-",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
}


def allowed_file(filename):
    name = str(filename or "")
    if (
        not name
        or name != os.path.basename(name)
        or "\x00" in name
        or ".." in name
    ):
        return False
    if "." not in name:
        return False
    extension = name.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def file_contents_match(filename, data):
    """Return whether the bytes match the filename's PDF, JPEG, or PNG signature."""
    if not allowed_file(filename) or not isinstance(data, (bytes, bytearray)):
        return False
    extension = str(filename).rsplit(".", 1)[1].lower()
    signature = _FILE_SIGNATURES.get(extension)
    return bool(signature) and bytes(data).startswith(signature)


def _query_profile_id():
    raw = request.args.get("profile_id")
    if raw is None or str(raw).strip() == "":
        return None, (
            jsonify({
                "success": False,
                "error": "profile_id is required",
            }),
            400,
        )
    text = str(raw).strip()
    if not text.isdigit():
        return None, (
            jsonify({
                "success": False,
                "error": "profile_id must be an integer between 1 and 5",
            }),
            400,
        )
    profile_id = int(text)
    if not 1 <= profile_id <= 5:
        return None, (
            jsonify({
                "success": False,
                "error": "profile_id must be an integer between 1 and 5",
            }),
            400,
        )
    return profile_id, None


def _path_inside_storage(storage_path):
    if not storage_path:
        return None
    root = os.path.realpath(STORAGE_DIR)
    candidate = os.path.realpath(storage_path)
    try:
        if os.path.commonpath([root, candidate]) != root:
            return None
    except ValueError:
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate



def build_extracted_data(extracted_text):
    """Convert OCR text into fields. Raw text is kept. Profile is not changed."""
    from app.document_reader import read_document_text

    return read_document_text(extracted_text)


def register_document_vault(app):
    from app.request_guard import install_request_guard

    install_request_guard(app)
    init_db()
    os.makedirs(STORAGE_DIR, exist_ok=True)

    @app.route("/api/documents/preview", methods=["POST"])
    def preview_document():
        try:
            profile_id = request.form.get("profile_id")
            doc_type = request.form.get("doc_type", "").strip().lower()
            capture_source = _capture_source(request.form.get("capture_source", "file"))
            if capture_source is None:
                return jsonify({
                    "success": False,
                    "error": "capture_source must be file or camera"
                }), 400
            try:
                profile_id = int(profile_id)
                if not profile_exists(profile_id):
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "error": "profile_id must refer to an existing valid profile"
                }), 400
            from app.ownership import guard_response
            denied = guard_response(profile_id)
            if denied is not None:
                return denied
            if doc_type not in ALLOWED_DOC_TYPES:
                return jsonify({
                    "success": False,
                    "error": "doc_type is not a supported document type"
                }), 400
            if "file" not in request.files:
                return jsonify({
                    "success": False,
                    "error": "file is required"
                }), 400
            file = request.files["file"]
            if not file.filename or not allowed_file(file.filename):
                return jsonify({
                    "success": False,
                    "error": "Only PDF, JPG, JPEG and PNG are allowed"
                }), 400
            data = file.read()
            if len(data) > MAX_FILE_SIZE:
                return jsonify({
                    "success": False,
                    "error": "Maximum file size is 10 MB"
                }), 400
            if not file_contents_match(file.filename, data):
                return jsonify({
                    "success": False,
                    "error": "File contents do not match a PDF, JPEG, or PNG"
                }), 400
            return jsonify({
                "success": True,
                "stored": False,
                "preview": {
                    "filename": file.filename,
                    "file_size": len(data),
                    "doc_type": doc_type,
                    "capture_source": capture_source,
                    "mime_type": file.mimetype or "",
                },
            })
        except Exception:
            return jsonify({
                "success": False,
                "error": "Request could not be completed"
            }), 500

    @app.route("/api/documents/upload", methods=["POST"])
    def upload_document():
        try:
            profile_id = request.form.get("profile_id")
            doc_type = request.form.get("doc_type", "").strip()

            if not profile_id:
                return jsonify({
                    "success": False,
                    "error": "profile_id is required"
                }), 400

            try:
                profile_id = int(profile_id)
                if not profile_exists(profile_id):
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "error": "profile_id must refer to an existing valid profile"
                }), 400

            from app.ownership import guard_response
            denied = guard_response(profile_id)
            if denied is not None:
                return denied

            if not doc_type:
                return jsonify({
                    "success": False,
                    "error": "doc_type is required"
                }), 400

            if doc_type.strip().lower() not in ALLOWED_DOC_TYPES:
                return jsonify({
                    "success": False,
                    "error": "doc_type is not a supported document type"
                }), 400
            doc_type = doc_type.strip().lower()
            capture_source = _capture_source(request.form.get("capture_source", "file"))
            if capture_source is None:
                return jsonify({
                    "success": False,
                    "error": "capture_source must be file or camera"
                }), 400

            if "file" not in request.files:
                return jsonify({
                    "success": False,
                    "error": "file is required"
                }), 400

            file = request.files["file"]

            if not file.filename:
                return jsonify({
                    "success": False,
                    "error": "filename is required"
                }), 400

            if not allowed_file(file.filename):
                return jsonify({
                    "success": False,
                    "error": "Only PDF, JPG, JPEG and PNG are allowed"
                }), 400

            data = file.read()

            if len(data) > MAX_FILE_SIZE:
                return jsonify({
                    "success": False,
                    "error": "Maximum file size is 10 MB"
                }), 400

            if not file_contents_match(file.filename, data):
                return jsonify({
                    "success": False,
                    "error": "File contents do not match a PDF, JPEG, or PNG"
                }), 400

            file_hash = hashlib.sha256(data).hexdigest()

            ext = file.filename.rsplit(".", 1)[1].lower()
            safe_name = f"{file_hash}.{ext}"

            profile_dir = os.path.join(STORAGE_DIR, str(profile_id))
            os.makedirs(profile_dir, exist_ok=True)

            storage_path = os.path.join(profile_dir, safe_name)

            from app.document_encryption import (
                DocumentStorageError,
                protect_text,
                read_for_ocr,
                store_bytes,
            )
            try:
                stored_bytes = store_bytes(data)
            except DocumentStorageError as error:
                return jsonify({"success": False, "error": str(error)}), 400

            with open(storage_path, "wb") as handle:
                handle.write(stored_bytes)

            extracted_text = ""
            structured_data = build_extracted_data("")
            processing_status = "processed"
            try:
                plain_text = read_for_ocr(storage_path, extract_text) or ""
                structured_data = build_extracted_data(plain_text)
                extracted_text = protect_text(plain_text)
                stored_structured = protect_text(
                    json.dumps(structured_data, ensure_ascii=False)
                )
            except DocumentStorageError:
                extracted_text = ""
                stored_structured = "{}"
                processing_status = "failed"
            except Exception:
                print("OCR WARNING: text extraction failed")
                extracted_text = ""
                stored_structured = "{}"
                processing_status = "failed"

            now = datetime.utcnow().isoformat()

            conn = get_db()

            existing = conn.execute(
                """
                SELECT id, document_reference FROM documents
                WHERE profile_id = ? AND file_hash = ?
                """,
                (profile_id, file_hash)
            ).fetchone()

            if existing:
                conn.close()
                os.remove(storage_path)

                return jsonify({
                    "success": True,
                    "message": "Document already exists",
                    "document_id": existing["id"],
                    "document_reference": existing["document_reference"]
                })

            version_row = conn.execute(
                """
                SELECT COALESCE(MAX(document_version), 0) AS latest_version
                FROM documents
                WHERE profile_id = ? AND doc_type = ?
                """,
                (profile_id, doc_type)
            ).fetchone()
            document_version = version_row["latest_version"] + 1
            document_reference = _generate_document_reference(conn)

            cursor = conn.execute(
                """
                INSERT INTO documents
                (
                    profile_id,
                    doc_type,
                    original_filename,
                    storage_path,
                    mime_type,
                    file_hash,
                    extracted_text,
                    extracted_data,
                    verified,
                    created_at,
                    updated_at,
                    document_version,
                    document_reference,
                    processing_status,
                    file_size,
                    capture_source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    doc_type,
                    file.filename,
                    storage_path,
                    file.mimetype or "",
                    file_hash,
                    extracted_text,
                    stored_structured,
                    0,
                    now,
                    now,
                    document_version,
                    document_reference,
                    processing_status,
                    len(data),
                    capture_source
                )
            )

            if document_version > 1:
                _clear_verified_profile(conn, profile_id)

            conn.commit()
            document_id = cursor.lastrowid
            conn.close()

            return jsonify({
                "success": True,
                "message": "Document uploaded successfully",
                "document_id": document_id,
                "filename": file.filename,
                "doc_type": doc_type,
                "document_version": document_version,
                "document_reference": document_reference,
                "processing_status": processing_status,
                "file_size": len(data),
                "capture_source": capture_source
            })

        except Exception:
            return jsonify({
                "success": False,
                "error": "Request could not be completed"
            }), 500


    @app.route("/api/documents/<int:profile_id>", methods=["GET"])
    def list_documents(profile_id):
        if not 1 <= profile_id <= 5:
            return jsonify({
                "success": False,
                "error": "profile_id must be an integer between 1 and 5"
            }), 400
        from app.ownership import guard_response
        denied = guard_response(profile_id)
        if denied is not None:
            return denied
        try:
            conn = get_db()

            rows = conn.execute(
                """
                SELECT
                    id,
                    profile_id,
                    doc_type,
                    original_filename,
                    mime_type,
                    file_hash,
                    extracted_text,
                    extracted_data,
                    verified,
                    created_at,
                    updated_at,
                    document_version,
                    document_reference,
                    processing_status,
                    file_size,
                    capture_source
                FROM documents
                WHERE profile_id = ?
                ORDER BY id DESC
                """,
                (profile_id,)
            ).fetchall()

            conn.close()

            from app.document_encryption import reveal_text
            documents = []
            for row in rows:
                item = dict(row)
                item["extracted_text"] = reveal_text(item.get("extracted_text"))
                item["extracted_data"] = reveal_text(item.get("extracted_data"))
                documents.append(item)

            return jsonify({
                "success": True,
                "count": len(documents),
                "documents": documents
            })

        except Exception:
            return jsonify({
                "success": False,
                "error": "Request could not be completed"
            }), 500


    @app.route("/api/documents/file/<int:document_id>", methods=["GET"])
    def download_document(document_id):
        profile_id, error = _query_profile_id()
        if error is not None:
            return error
        from app.ownership import guard_response
        denied = guard_response(profile_id)
        if denied is not None:
            return denied
        try:
            conn = get_db()

            row = conn.execute(
                """
                SELECT storage_path, original_filename, profile_id, mime_type
                FROM documents
                WHERE id = ? AND profile_id = ?
                """,
                (document_id, profile_id)
            ).fetchone()

            conn.close()

            if not row:
                return jsonify({
                    "success": False,
                    "error": "Document not found"
                }), 404

            stored_file = _path_inside_storage(row["storage_path"])
            if stored_file is None:
                return jsonify({
                    "success": False,
                    "error": "Stored file not found"
                }), 404

            from io import BytesIO
            from app.document_encryption import DocumentStorageError, read_bytes
            try:
                payload = read_bytes(stored_file)
            except (DocumentStorageError, OSError):
                return jsonify({
                    "success": False,
                    "error": "Stored file could not be read"
                }), 404

            return send_file(
                BytesIO(payload),
                as_attachment=False,
                download_name=os.path.basename(row["original_filename"] or "document"),
                mimetype=row["mime_type"] or None,
            )

        except Exception:
            return jsonify({
                "success": False,
                "error": "Request could not be completed"
            }), 500


    @app.route("/api/documents/<int:document_id>", methods=["DELETE"])
    def delete_document(document_id):
        profile_id, error = _query_profile_id()
        if error is not None:
            return error
        from app.ownership import guard_response
        denied = guard_response(profile_id)
        if denied is not None:
            return denied
        try:
            conn = get_db()

            row = conn.execute(
                """
                SELECT storage_path, profile_id
                FROM documents
                WHERE id = ? AND profile_id = ?
                """,
                (document_id, profile_id)
            ).fetchone()

            if not row:
                conn.close()
                return jsonify({
                    "success": False,
                    "error": "Document not found"
                }), 404

            stored_file = _path_inside_storage(row["storage_path"])
            if stored_file is not None:
                os.remove(stored_file)

            conn.execute(
                "DELETE FROM documents WHERE id = ? AND profile_id = ?",
                (document_id, profile_id)
            )
            _clear_verified_profile(conn, row["profile_id"])

            conn.commit()
            conn.close()

            return jsonify({
                "success": True,
                "message": "Document deleted successfully"
            })

        except Exception:
            return jsonify({
                "success": False,
                "error": "Request could not be completed"
            }), 500


    print("Document Vault registered successfully.")
DOCUMENT_VAULT_PAGE = """
<!doctype html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FormBharat - Document Vault</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f7f6;margin:0;padding:20px}
.container{max-width:700px;margin:auto}.card{background:#fff;padding:20px;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:15px}
h1{color:#146c43}label{display:block;margin-top:14px;margin-bottom:6px;font-weight:bold}
input{width:100%;box-sizing:border-box;padding:13px;border:1px solid #ccc;border-radius:8px;font-size:16px}
button{width:100%;margin-top:15px;padding:13px;background:#146c43;color:#fff;border:0;border-radius:8px;font-size:16px;font-weight:bold}
.doc{padding:12px;border-bottom:1px solid #ddd}.delete{background:#b3261e}
</style></head>
<body><div class="container">
<div class="card"><h1>Documents Manage</h1><p>Photo, signature aur identity documents yahin save hote hain.</p>
<p>पुरानी फाइलें मूल bytes में रहती हैं और दोबारा नहीं लिखी जातीं। नई upload तभी encrypt होती है जब document key लगी हो। Key आवश्यक हो और उपलब्ध न हो, तो upload रुक जाती है।</p>
<form id="uploadForm">
<input id="profile_id" type="hidden" value="{{ profile_slot }}">
<label>Document Type</label><input id="doc_type" placeholder="Aadhaar / Marksheet / Other" required>
<label>Select File</label><input id="file" type="file" accept=".pdf,.jpg,.jpeg,.png">
<label>Camera</label><input id="camera" type="file" accept="image/*" capture="environment">
<img id="preview" alt="Document preview" style="display:none;max-width:100%;margin-top:12px">
<button type="submit">Upload Document</button>
</form><p id="message"></p></div>
<div class="card"><h2>Saved Documents</h2><button onclick="loadDocuments()">Refresh Documents</button><div id="documents"></div></div>
</div>
<script>
const msg=document.getElementById('message'),docs=document.getElementById('documents');
async function csrfHeaders(){
 const response=await fetch('/api/csrf');
 const body=await response.json();
 return {'X-FormBharat-Token': body.token||''};
}
let captureSource='file';
function showPreview(input, source){
 const chosen=input.files[0];
 if(!chosen)return;
 captureSource=source;
 const image=document.getElementById('preview');
 image.style.display='block';
 image.src=URL.createObjectURL(chosen);
}
document.getElementById('file').onchange=e=>showPreview(e.target,'file');
document.getElementById('camera').onchange=e=>showPreview(e.target,'camera');
async function loadDocuments(){
 const id=document.getElementById('profile_id').value||1;
 const r=await fetch('/api/documents/'+encodeURIComponent(id)),d=await r.json();
 docs.replaceChildren();
 if(!d.success){docs.textContent='Error: '+(d.error||'Could not load documents.');return}
 if(!d.documents.length){docs.textContent='No documents saved yet';return}
 d.documents.forEach(function(item){
  const block=document.createElement('div');
  block.className='doc';
  const title=document.createElement('b');
  title.textContent=item.doc_type||'';
  block.appendChild(title);
  block.appendChild(document.createElement('br'));
  block.appendChild(document.createTextNode(item.original_filename||''));
  block.appendChild(document.createElement('br'));
  block.appendChild(document.createTextNode('Version: '+(item.document_version??'')));
  block.appendChild(document.createElement('br'));
  block.appendChild(document.createTextNode('Verified: '+(item.verified ? 'yes' : 'no')));
  block.appendChild(document.createElement('br'));
  block.appendChild(document.createTextNode('Processing: '+(item.processing_status||'unknown')+'. OCR is not verification.'));
  block.appendChild(document.createElement('br'));
  let readData={};
  try{readData=JSON.parse(item.extracted_data||'{}');}catch(error){readData={};}
  const readRows=[];
  if(readData.name)readRows.push('नाम: '+readData.name);
  if(readData.father_name)readRows.push('पिता: '+readData.father_name);
  if(readData.dob)readRows.push('जन्म तिथि: '+readData.dob);
  if(readData.gender)readRows.push('लिंग: '+readData.gender);
  if(readData.pan_number)readRows.push('पैन: '+readData.pan_number);
  if(readData.aadhaar_number)readRows.push('आधार: '+readData.aadhaar_number);
  if(readData.roll_number)readRows.push('रोल: '+readData.roll_number);
  if(!readRows.length)readRows.push('पढ़ा नहीं गया।');
  readRows.forEach(function(row){
   block.appendChild(document.createTextNode(row));
   block.appendChild(document.createElement('br'));
  });
  const link=document.createElement('a');
  link.href='/api/documents/file/'+encodeURIComponent(item.id)+'?profile_id='+encodeURIComponent(id);
  link.target='_blank';
  link.textContent='View File';
  block.appendChild(link);
  const button=document.createElement('button');
  button.className='delete';
  button.type='button';
  button.textContent='Delete';
  button.onclick=function(){deleteDocument(item.id);};
  block.appendChild(button);
  docs.appendChild(block);
 });
}
async function deleteDocument(id){
 if(!confirm('Delete this document?'))return;
 const profileId=document.getElementById('profile_id').value||1;
 const headers=await csrfHeaders();
 const r=await fetch('/api/documents/'+encodeURIComponent(id)+'?profile_id='+encodeURIComponent(profileId),{method:'DELETE',headers}),d=await r.json();
 msg.textContent=d.message||d.error;loadDocuments();
}
document.getElementById('uploadForm').onsubmit=async e=>{
 e.preventDefault();msg.textContent='Uploading...';
 const f=new FormData();
 f.append('profile_id',document.getElementById('profile_id').value);
 f.append('doc_type',document.getElementById('doc_type').value);
 f.append('capture_source',captureSource);
 const camera=document.getElementById('camera').files[0];
 const chosen=captureSource==='camera'&&camera?camera:document.getElementById('file').files[0];
 f.append('file',chosen);
 const headers=await csrfHeaders();
 const r=await fetch('/api/documents/upload',{method:'POST',body:f,headers}),d=await r.json();
 msg.textContent=d.message||d.error;
 if(d.success){document.getElementById('file').value='';loadDocuments()}
};
loadDocuments();
</script></body></html>
"""

def register_document_vault_ui(app):
    @app.route("/documents", methods=["GET"])
    def document_vault_page():
        from app.ownership import SlotAccessError, current_user_id, owned_slot_for_session

        profile_slot = 1
        if current_user_id() is not None:
            try:
                profile_slot = owned_slot_for_session()
            except SlotAccessError:
                profile_slot = ""
        return render_template_string(
            DOCUMENT_VAULT_PAGE,
            profile_slot=profile_slot,
        )
