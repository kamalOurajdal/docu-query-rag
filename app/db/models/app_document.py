from app.db.document import Document


class AppDocument(Document):
    __TABLE__ = "app_documents"

    _id = None
    name = None
    description = None
    tags = None
    file_metadata = None
    embedding = None
    created_on = None

    def get_file_metadata(self):
        return self.file_metadata
