from email.mime.image import MIMEImage

from django.conf import settings


HAPPYNESS_LOGO_CID = "happyness-project-logo"


def attach_happyness_logo(email_message):
    logo_path = settings.BASE_DIR / "webapp" / "static" / "media" / "Happyness Project.jpg"
    with logo_path.open("rb") as logo_file:
        logo = MIMEImage(logo_file.read(), _subtype="jpeg")

    logo.add_header("Content-ID", f"<{HAPPYNESS_LOGO_CID}>")
    logo.add_header("Content-Disposition", "inline", filename="happyness-project-logo.jpg")
    email_message.attach(logo)
