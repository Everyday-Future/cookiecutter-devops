from marshmallow import Schema, fields, validate, validates, ValidationError


class UserSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=1, max=80))
    email = fields.Email(required=True)
    role = fields.Str(required=True, validate=validate.Length(min=1, max=16))
    password = fields.Str(required=True, validate=validate.Regexp(
        r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$',
        error="Password must contain at least 8 characters, one letter and one number")
    )

    @validates('username')
    def validate_username(self, value):
        if 'admin' in value.lower():
            raise ValidationError('Username cannot contain "admin"')
