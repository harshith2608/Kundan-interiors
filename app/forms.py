from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FloatField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, NumberRange, Regexp


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=80, message='Username must be 3–80 characters.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    submit = SubmitField('Sign In')


class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=80, message='Username must be 3–80 characters.'),
        Regexp(r'^[\w.@+-]+$', message='Only letters, numbers, and @/./+/-/_ allowed.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=6, message='Password must be at least 6 characters.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    role = SelectField('Role', choices=[('employee', 'Employee'), ('admin', 'Admin')],
                       validators=[DataRequired()])
    submit = SubmitField('Create User')


class WoodRateForm(FlaskForm):
    acrylic_rate = FloatField('Acrylic (Rs./sqft)', validators=[
        DataRequired(), NumberRange(min=0, message='Rate must be positive.')
    ])
    laminates_rate = FloatField('Laminates (Rs./sqft)', validators=[
        DataRequired(), NumberRange(min=0, message='Rate must be positive.')
    ])
    veneer_rate = FloatField('Veneer (Rs./sqft)', validators=[
        DataRequired(), NumberRange(min=0, message='Rate must be positive.')
    ])
    submit = SubmitField('Update Rates')


class ChangePasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Change Password')
