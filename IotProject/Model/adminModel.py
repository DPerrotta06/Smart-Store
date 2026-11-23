from Database.db import db


class Admin(db.Model):
    """Someone allowed to use the admin page. admin_id is their customer membership number."""
    __tablename__ = "Admin"
    admin_id = db.Column(db.Integer, db.ForeignKey("Customer.membership_number"), primary_key=True)


def isAdmin(membership_number):
    """True when this customer is listed in the Admin table. Read from the database every time."""
    return db.session.get(Admin, membership_number) is not None