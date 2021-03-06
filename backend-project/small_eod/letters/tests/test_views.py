from django.urls import reverse
import requests
from io import BytesIO

from ..factories import LetterFactory

from rest_framework import status
from rest_framework.test import APITestCase


class PresignedUploadFileTestCase(APITestCase):
    def test_getting_form_data(self):
        url = reverse("file_upload")
        data = {
            "name": "text.file",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("formData", response.data)

        form_data = response.data["formData"]
        self.assertIn("bucket", form_data)
        self.assertIn("key", form_data)
        self.assertIn("policy", form_data)
        self.assertIn("x-amz-algorithm", form_data)
        self.assertIn("x-amz-credential", form_data)
        self.assertIn("x-amz-date", form_data)
        self.assertIn("x-amz-signature", form_data)

    def test_file_upload_and_download(self):
        url = reverse("file_upload")
        data = {
            "name": "text.file",
        }
        content = b"xxx"

        # Upload file
        backend_resp = self.client.post(url, data, format="json")
        minio_upload_resp = requests.post(
            url=backend_resp.data["url"],
            data=backend_resp.data["formData"],
            files={"file": BytesIO(content)},
        )
        self.assertEqual(minio_upload_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Create a file
        url = reverse("letter-files-list", kwargs={"letter_pk": LetterFactory().pk})

        response = self.client.post(url, backend_resp.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Download file content
        minio_download_resp = requests.get(url=response.json()["downloadUrl"],)
        self.assertEqual(minio_download_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(minio_download_resp.content, content)


class FileCreateTestCase(APITestCase):
    def test_file_not_found(self):
        url = reverse("letter-files-list", kwargs={"letter_pk": 0})
        data = {"path": "path/to/file", "name": "test.file"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_file_created(self):
        letter = LetterFactory()

        url = reverse("letter-files-list", kwargs={"letter_pk": letter.pk})
        data = {"path": "path/to/file", "name": "test.file"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["path"], data["path"])
        self.assertIn("id", response.data)
