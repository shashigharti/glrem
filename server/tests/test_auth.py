import unittest
from unittest.mock import MagicMock, patch
from src.models import User
from src.crud.auth import authenticate_user

example_hashed_password = "$2b$12$CwTycUXWzJ3H7uBOpnP.S.xGFCk2U8X0H9lBe4GvZ1ZX42g6zUn0q"


class TestAuthenticateUser(unittest.TestCase):

    @patch("src.crud.auth.pwd_context.verify")
    @patch("src.crud.auth.Session")
    def test_authenticate_user(self, MockSession, mock_verify):
        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.hashed_password = example_hashed_password

        mock_session_instance = MockSession.return_value
        mock_session_instance.query.return_value.filter.return_value.first.return_value = (
            mock_user
        )

        mock_verify.return_value = True

        db = MockSession()
        user = authenticate_user(db, "admin", "admin123")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "admin")

        mock_verify.return_value = False
        user = authenticate_user(db, "admin", "wrongpassword")
        self.assertIsNone(user)

        mock_session_instance.query.return_value.filter.return_value.first.return_value = (
            None
        )
        user = authenticate_user(db, "nonexistentuser", "admin123")
        self.assertIsNone(user)


if __name__ == "__main__":
    unittest.main()
