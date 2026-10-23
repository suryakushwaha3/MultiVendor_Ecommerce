from datetime import datetime, timezone

from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    recipient_type = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )
    # user, vendor, admin

    recipient_id = db.Column(
        db.Integer,
        nullable=True,
        index=True
    )
    # Admin notifications can use a null recipient_id.

    title = db.Column(
        db.String(150),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    notification_type = db.Column(
        db.String(50),
        nullable=False,
        default="general"
    )
    # order, payment, product, promotion, general

    reference_type = db.Column(
        db.String(50),
        nullable=True
    )

    reference_id = db.Column(
        db.Integer,
        nullable=True,
        index=True
    )

    action_url = db.Column(
        db.String(500),
        nullable=True
    )

    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True
    )

    read_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "recipient_type IN ('user', 'vendor', 'admin')",
            name="ck_notification_recipient_type"
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "recipient_type": self.recipient_type,
            "recipient_id": self.recipient_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "action_url": self.action_url,
            "is_read": self.is_read,
            "read_at": (
                self.read_at.isoformat()
                if self.read_at else None
            ),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )
        }