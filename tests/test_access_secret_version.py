import unittest
from unittest import mock
import os

# Assuming access_secret_version is in automated_sync.py for testing purposes
# In a real refactor, this would be in a shared utility file.
from automated_sync import access_secret_version

class TestAccessSecretVersion(unittest.TestCase):

    @mock.patch('automated_sync.secretmanager.SecretManagerServiceClient')
    def test_access_secret_version_is_secret_path(self, mock_client_class):
        """
        Test that access_secret_version correctly retrieves a secret
        when a secret path is provided.
        """
        mock_client_instance = mock_client_class.return_value
        mock_client_instance.access_secret_version.return_value.payload.data = b"test_secret_value"

        secret_path = "projects/123/secrets/my-secret/versions/1"
        result = access_secret_version(secret_path)

        mock_client_class.assert_called_once()
        mock_client_instance.access_secret_version.assert_called_once_with(name=secret_path)
        self.assertEqual(result, "test_secret_value")

    @mock.patch('automated_sync.secretmanager.SecretManagerServiceClient')
    def test_access_secret_version_not_secret_path(self, mock_client_class):
        """
        Test that access_secret_version returns the input directly
        when it's not a secret path.
        """
        not_a_secret_path = "just_a_string"
        result = access_secret_version(not_a_secret_path)

        mock_client_class.assert_not_called()
        self.assertEqual(result, "just_a_string")

    @mock.patch('automated_sync.secretmanager.SecretManagerServiceClient')
    def test_access_secret_version_raises_exception(self, mock_client_class):
        """
        Test that access_secret_version raises an exception when
        secretmanager.SecretManagerServiceClient fails.
        """
        mock_client_instance = mock_client_class.return_value
        mock_client_instance.access_secret_version.side_effect = Exception("API Error")

        secret_path = "projects/123/secrets/my-secret/versions/1"
        with self.assertRaisesRegex(Exception, "API Error"):
            access_secret_version(secret_path)

        mock_client_class.assert_called_once()
        mock_client_instance.access_secret_version.assert_called_once_with(name=secret_path)

if __name__ == '__main__':
    unittest.main()
