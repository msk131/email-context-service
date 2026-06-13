from app.models.email import Email


def test_email_body_is_encrypted_at_rest():
    email = Email(body={"contentType": "Text", "content": "Sensitive CPA email"})

    assert email.body_encrypted
    assert "Sensitive CPA email" not in email.body_encrypted
    assert email.body == {"contentType": "Text", "content": "Sensitive CPA email"}
    assert email.body_text == "Sensitive CPA email"
