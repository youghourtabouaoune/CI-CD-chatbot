import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@cicd-helper.com')
        self.app_name = os.environ.get('APP_NAME', 'CI/CD Helper')
        self.base_url = os.environ.get('BASE_URL', 'http://localhost:5000')

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Send email using SMTP"""
        if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
            print("SMTP configuration missing. Email not sent.")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.app_name} <{self.from_email}>"
            msg['To'] = to_email

            # Add text/plain and text/html parts
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)

            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            print(f"Email sent to {to_email}")
            return True

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def send_email_verification(self, to_email: str, verification_token: str, first_name: str = None) -> bool:
        """Send email verification email"""
        verification_url = f"{self.base_url}/verify-email?token={verification_token}"
        
        subject = f"Verify Your Email - {self.app_name}"
        
        greeting = f"Hello {first_name}," if first_name else "Hello,"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3a86ff, #8338ec); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #3a86ff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                .code {{ background: #f4f4f4; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name}</h1>
                </div>
                <div class="content">
                    <h2>Verify Your Email Address</h2>
                    <p>{greeting}</p>
                    <p>Thank you for signing up! Please verify your email address to complete your registration and start using {self.app_name}.</p>
                    
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <div class="code">{verification_url}</div>
                    
                    <p>This verification link will expire in 24 hours.</p>
                    
                    <p>If you didn't create an account with {self.app_name}, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Verify Your Email Address
        
        {greeting}
        
        Thank you for signing up! Please verify your email address to complete your registration and start using {self.app_name}.
        
        Click this link to verify your email: {verification_url}
        
        This verification link will expire in 24 hours.
        
        If you didn't create an account with {self.app_name}, please ignore this email.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

    def send_password_reset_email(self, to_email: str, reset_token: str, first_name: str = None) -> bool:
        """Send password reset email"""
        reset_url = f"{self.base_url}/reset-password?token={reset_token}"
        
        subject = f"Reset Your Password - {self.app_name}"
        
        greeting = f"Hello {first_name}," if first_name else "Hello,"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3a86ff, #8338ec); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #3a86ff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                .code {{ background: #f4f4f4; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name}</h1>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>{greeting}</p>
                    <p>You requested to reset your password for your {self.app_name} account.</p>
                    
                    <div class="warning">
                        <strong>Important:</strong> This link will expire in 1 hour for security reasons.
                    </div>
                    
                    <a href="{reset_url}" class="button">Reset Password</a>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <div class="code">{reset_url}</div>
                    
                    <p>If you didn't request this reset, please ignore this email. Your account remains secure.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request
        
        {greeting}
        
        You requested to reset your password for your {self.app_name} account.
        
        Click this link to reset your password: {reset_url}
        
        Important: This link will expire in 1 hour for security reasons.
        
        If you didn't request this reset, please ignore this email. Your account remains secure.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

    def send_welcome_email(self, to_email: str, first_name: str) -> bool:
        """Send welcome email to new users"""
        subject = f"Welcome to {self.app_name}!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3a86ff, #8338ec); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .feature {{ margin: 15px 0; padding: 10px; background: white; border-radius: 5px; border-left: 4px solid #3a86ff; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {self.app_name}!</h1>
                </div>
                <div class="content">
                    <h2>Hello {first_name},</h2>
                    <p>Thank you for joining {self.app_name}! We're excited to help you streamline your CI/CD pipeline development.</p>
                    
                    <h3>What you can do:</h3>
                    <div class="feature">
                        <strong>🤖 AI-Powered Code Generation</strong>
                        <p>Generate CI/CD pipelines, GitHub Actions, Jenkins files, and more with AI assistance.</p>
                    </div>
                    <div class="feature">
                        <strong>💾 Save & Manage Conversations</strong>
                        <p>Keep track of all your generated code and conversations.</p>
                    </div>
                    <div class="feature">
                        <strong>🚀 100 Generations Per Hour</strong>
                        <p>As a registered user, you get 100 AI generations per hour instead of just 5.</p>
                    </div>
                    
                    <p>Get started by visiting: <a href="{self.base_url}">{self.base_url}</a></p>
                    
                    <p>If you have any questions, check out our documentation or contact support.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to {self.app_name}!
        
        Hello {first_name},
        
        Thank you for joining {self.app_name}! We're excited to help you streamline your CI/CD pipeline development.
        
        What you can do:
        - AI-Powered Code Generation: Generate CI/CD pipelines, GitHub Actions, Jenkins files, and more
        - Save & Manage Conversations: Keep track of all your generated code and conversations
        - 100 Generations Per Hour: As a registered user, you get 100 AI generations per hour
        
        Get started by visiting: {self.base_url}
        
        If you have any questions, check out our documentation or contact support.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

    def send_account_locked_email(self, to_email: str, first_name: str, unlock_time: str) -> bool:
        """Send account locked notification email"""
        subject = f"Account Locked - {self.app_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .warning {{ background: #ffeaa7; border: 1px solid #fdcb6e; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Account Security Notice</h1>
                </div>
                <div class="content">
                    <h2>Hello {first_name},</h2>
                    
                    <div class="warning">
                        <strong>Security Alert:</strong> Your account has been temporarily locked due to multiple failed login attempts.
                    </div>
                    
                    <p>For your security, we've locked your account until <strong>{unlock_time}</strong>.</p>
                    
                    <p><strong>What happened?</strong><br>
                    There were too many unsuccessful login attempts to your account.</p>
                    
                    <p><strong>What should you do?</strong><br>
                    - Wait until the lockout period ends<br>
                    - Use the "Forgot Password" feature if you've forgotten your password<br>
                    - Ensure you're using the correct email and password combination</p>
                    
                    <p>If you believe this was a mistake or need immediate assistance, please contact our support team.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} {self.app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)