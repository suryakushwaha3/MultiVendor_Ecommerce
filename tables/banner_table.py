from datetime import datetime, timezone

from app.extensions import db


class Banner(db.Model):
    __tablename__ = "banners"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    subtitle = db.Column(
        db.String(255),
        nullable=True
    )

    image_url = db.Column(
        db.String(500),
        nullable=False
    )

    redirect_url = db.Column(
        db.String(500),
        nullable=True
    )

    position = db.Column(
        db.String(50),
        nullable=False,
        default="home"
    )

    display_order = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    starts_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    ends_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "image_url": self.image_url,
            "redirect_url": self.redirect_url,
            "position": self.position,
            "display_order": self.display_order,
            "starts_at": (
                self.starts_at.isoformat()
                if self.starts_at else None
            ),
            "ends_at": (
                self.ends_at.isoformat()
                if self.ends_at else None
            ),
            "is_active": self.is_active,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }