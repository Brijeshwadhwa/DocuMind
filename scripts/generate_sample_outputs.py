import json
import os
import sys
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.document import Document
from app.processors.pipeline import DocumentPipeline
from app.services.relationship_service import RelationshipService
from app.schemas.document import DocumentRelationshipCreate
from app.schemas.question import QuestionResponse
from app.schemas.review_item import ReviewItemResponse


def generate_outputs():
    os.makedirs("sample_outputs", exist_ok=True)
    db = SessionLocal()

    user = db.query(User).filter(User.email == "sample_outputs@example.com").first()
    if not user:
        user = User(email="sample_outputs@example.com", password_hash="dummyhash")
        db.add(user)
        db.commit()
        db.refresh(user)

    def process_and_dump(filename: str, out_name: str, link_ak: bool = False, ak_filename: str = None):
        storage_path = os.path.abspath(f"./storage/uploads/out_{filename}")
        shutil.copy(f"sample_documents/{filename}", storage_path)
        content_type = "application/pdf" if filename.endswith(".pdf") else "image/png"

        doc = Document(
            owner_id=user.id,
            filename=filename,
            content_type=content_type,
            file_size=os.path.getsize(storage_path),
            storage_path=storage_path,
            status="PENDING"
        )
        db.add(doc)
        db.commit()

        pipeline = DocumentPipeline(db=db)
        pipeline.process_document(doc.id)

        if link_ak and ak_filename:
            ak_storage = os.path.abspath(f"./storage/uploads/out_{ak_filename}")
            shutil.copy(f"sample_documents/{ak_filename}", ak_storage)
            ak_doc = Document(
                owner_id=user.id,
                filename=ak_filename,
                content_type="application/pdf",
                file_size=os.path.getsize(ak_storage),
                storage_path=ak_storage,
                status="PENDING"
            )
            db.add(ak_doc)
            db.commit()
            pipeline.process_document(ak_doc.id)

            rel_service = RelationshipService(db)
            rel_service.create_relationship(
                doc.id,
                DocumentRelationshipCreate(
                    related_document_id=ak_doc.id,
                    relationship_type="ANSWER_KEY"
                ),
                user.id
            )

        db.refresh(doc)
        output_payload = {
            "document_id": doc.id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "status": doc.status,
            "total_questions": len(doc.questions),
            "questions": [QuestionResponse.model_validate(q).model_dump(by_alias=True) for q in doc.questions],
            "total_review_items": len(doc.review_items),
            "review_items": [ReviewItemResponse.model_validate(r).model_dump() for r in doc.review_items],
        }

        out_path = os.path.join("sample_outputs", out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2, default=str)
        print(f"Generated {out_path} ({len(doc.questions)} questions, {len(doc.review_items)} review items)")

    process_and_dump("01_clean_digital_exam.pdf", "01_clean_digital_output.json")
    process_and_dump("02_image_question_paper.png", "02_image_exam_output.json")
    process_and_dump("03_scanned_noisy_exam.pdf", "03_scanned_noisy_output.json")
    process_and_dump("04_multipage_continuation.pdf", "04_multipage_output.json")
    process_and_dump(
        "05a_question_paper_only.pdf",
        "05_associated_relationship_output.json",
        link_ak=True,
        ak_filename="05b_separate_answer_key.pdf"
    )

    db.close()
    print("\nAll sample output JSON files successfully generated in sample_outputs/")


if __name__ == "__main__":
    generate_outputs()
