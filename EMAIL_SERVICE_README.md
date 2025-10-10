# Email Service Documentation

## Overview

This email service provides a production-ready AWS SES integration with comprehensive features for sending, tracking, and managing emails in the Health App.

## Features

### ✅ Core Features
- **AWS SES Integration**: Full integration with Amazon Simple Email Service
- **Email Sending**: Send HTML and text emails with tracking
- **Bounce Handling**: Automatic bounce processing and suppression lists
- **Complaint Handling**: Spam complaint processing and list management
- **Unsubscribe Management**: One-click unsubscribe with suppression lists
- **Email Tracking**: Comprehensive logging and analytics
- **Template System**: Dynamic email templates (ready for implementation)
- **Webhook Support**: SES notification handling for bounces/complaints

### ✅ Production-Ready Features
- **Rate Limiting**: Respects SES sending limits
- **Error Handling**: Comprehensive retry logic and error reporting
- **Email Quality**: Content validation and spam score checking
- **Delivery Tracking**: Open/click tracking, delivery status
- **Analytics**: Email statistics and performance metrics
- **Security**: Proper authentication and authorization

## Setup

### 1. Environment Variables

Add these to your `.env` file:

```bash
# AWS SES Configuration (Required)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# SES Email Configuration (Required)
SES_FROM_EMAIL=noreply@yourdomain.com
SES_FROM_NAME=Health App

# Optional SES Configuration
SES_REPLY_TO=support@yourdomain.com
SES_CONFIGURATION_SET=your_configuration_set
SES_BOUNCE_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:bounces
SES_COMPLAINT_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:complaints
SES_DELIVERY_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:deliveries
```

### 2. Database Migration

Run the migration to create email tables:

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### 3. AWS SES Setup

1. **Verify your domain/email** in AWS SES console
2. **Request production access** if needed
3. **Set up SNS topics** for bounce/complaint notifications
4. **Configure webhook endpoint** to receive notifications

## Usage

### Basic Email Sending

```python
from app.services.email_service import EmailService

email_service = EmailService()

result = await email_service.send_email(
    to_emails=["user@example.com"],
    subject="Welcome to Health App!",
    html_content="<h1>Welcome!</h1><p>Thank you for joining us.</p>",
    text_content="Welcome! Thank you for joining us.",
    template_name="welcome_email"
)
```

### Using Email Utilities

```python
from app.services.email_utils import email_utils

# Send welcome email
await email_utils.send_welcome_email(
    user_email="user@example.com",
    user_name="John Doe"
)

# Send password reset
await email_utils.send_password_reset_email(
    user_email="user@example.com",
    reset_token="abc123",
    user_name="John Doe"
)

# Send crisis alert
await email_utils.send_crisis_alert(
    support_emails=["support@yourdomain.com"],
    user_identifier="user123",
    session_id="session456",
    risk_level="high"
)
```

### API Endpoints

#### Send Email
```http
POST /api/v1/email/send
Content-Type: application/json

{
    "to_emails": ["user@example.com"],
    "subject": "Welcome to Health App!",
    "html_content": "<h1>Welcome!</h1>",
    "text_content": "Welcome!",
    "template_name": "welcome_email"
}
```

#### Get Email Logs
```http
GET /api/v1/email/logs?page=1&limit=50&status=delivered
```

#### Get Email Statistics
```http
GET /api/v1/email/stats?days=30
```

#### Unsubscribe Email
```http
POST /api/v1/email/unsubscribe
Content-Type: application/json

{
    "email": "user@example.com",
    "reason": "Too many emails"
}
```

#### SES Webhook (for bounces/complaints)
```http
POST /api/v1/email/ses/webhook
Content-Type: application/json

{
    "notificationType": "Bounce",
    "mail": {...},
    "bounce": {...}
}
```

## Database Schema

### Email Tables

- **email_logs**: Track all email sends and their status
- **email_unsubscribes**: List of unsubscribed email addresses
- **email_templates**: Email templates (ready for future use)
- **email_bounces**: Bounce records from SES
- **email_complaints**: Complaint records from SES

## Testing

Run the test script to verify everything works:

```bash
cd backend
python test_email_service.py
```

Make sure to set `TEST_EMAIL` in your environment variables for testing.

## Production Considerations

### 1. AWS SES Limits
- **Sandbox**: 200 emails/day, 1 email/second
- **Production**: Request limit increases as needed
- **Bounce Rate**: Keep below 5%
- **Complaint Rate**: Keep below 0.1%

### 2. Email Quality
- Use proper HTML structure
- Include text versions
- Avoid spam trigger words
- Use proper authentication (SPF, DKIM, DMARC)

### 3. Monitoring
- Monitor bounce and complaint rates
- Set up CloudWatch alarms
- Track delivery rates
- Monitor sender reputation

### 4. Webhook Security
- Verify SNS message signatures
- Use HTTPS endpoints
- Implement proper authentication
- Handle duplicate notifications

## Common Use Cases

### 1. User Authentication
- Welcome emails
- Email verification
- Password reset
- Login notifications

### 2. Employee Management
- Access requests
- HR notifications
- Bulk invitations
- Approval/rejection emails

### 3. Mental Health App
- Assessment reminders
- Session notifications
- Crisis alerts
- Support team notifications

### 4. System Notifications
- Subscription confirmations
- Payment receipts
- Maintenance alerts
- Security alerts

## Troubleshooting

### Common Issues

1. **"Sender email not verified"**
   - Verify your sender email in AWS SES console
   - Check domain verification if using custom domain

2. **"Rate limit exceeded"**
   - Check your SES sending limits
   - Implement proper rate limiting in your code

3. **"Bounce rate too high"**
   - Clean your email lists
   - Remove invalid email addresses
   - Use double opt-in

4. **"Complaint rate too high"**
   - Review email content
   - Ensure proper unsubscribe links
   - Follow email best practices

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('app.services.email_service').setLevel(logging.DEBUG)
```

## Future Enhancements

- [ ] Template system with Jinja2
- [ ] A/B testing for emails
- [ ] Advanced analytics and reporting
- [ ] Email scheduling
- [ ] Bulk email campaigns
- [ ] Email personalization
- [ ] Advanced tracking (opens, clicks)
- [ ] Email automation workflows

## Support

For issues or questions:
1. Check the logs in `app.log`
2. Review AWS SES console for errors
3. Test with the provided test script
4. Check database for email logs and errors

## Security Notes

- Never expose AWS credentials in code
- Use IAM roles with minimal permissions
- Implement proper authentication for API endpoints
- Validate all email inputs
- Handle sensitive data appropriately
- Follow GDPR/privacy regulations for email data
