# AWS SES Setup Guide for MindAcuity

## 🚨 Current Issue
Your email `noreply@mindacuity.ai` is not verified in AWS SES. You need to verify it first.

## 📋 Step-by-Step Setup

### Step 1: Verify Your Email Address

1. **Go to AWS SES Console**
   - Open AWS Console → Services → Simple Email Service (SES)
   - Make sure you're in the correct region (ap-south-1 based on your test)

2. **Navigate to Verified Identities**
   - Click on "Verified identities" in the left sidebar
   - Click "Create identity"

3. **Create Email Identity**
   - Select "Email address"
   - Enter: `noreply@mindacuity.ai`
   - Click "Create identity"

4. **Check Your Email**
   - AWS will send a verification email to `noreply@mindacuity.ai`
   - Check the email inbox
   - Click the verification link in the email

5. **Verify Domain (Recommended)**
   - Go back to "Verified identities"
   - Click "Create identity" again
   - Select "Domain"
   - Enter: `mindacuity.ai`
   - Follow the DNS setup instructions
   - This allows you to send from any email @mindacuity.ai

### Step 2: Request Production Access

1. **Go to Account Dashboard**
   - In SES Console, click "Account dashboard"
   - You'll see "Sending statistics" and "Sending limits"

2. **Request Production Access**
   - Click "Request production access"
   - Fill out the form:
     - **Mail type**: Transactional
     - **Website URL**: https://mindacuity.ai
     - **Use case description**: 
       ```
       We are a mental health application that sends:
       - Welcome emails to new users
       - Password reset emails
       - Account verification emails
       - HR notifications for employee access
       - Crisis alerts to support team
       - Subscription confirmations
       
       We follow email best practices and have proper unsubscribe mechanisms.
       ```
     - **Expected daily volume**: Start with 1000 emails/day
     - **Bounce handling**: Yes, we have automated bounce handling
     - **Complaint handling**: Yes, we have automated complaint handling

3. **Wait for Approval**
   - Usually takes 24-48 hours
   - You'll get an email when approved

### Step 3: Test Your Setup

Once your email is verified, run the test again:

```bash
cd backend
python test_email_service.py
```

## 🔧 Current Configuration

Your current settings are:
- **From Email**: `noreply@mindacuity.ai`
- **From Name**: `MindAcuity`
- **Reply To**: `support@mindacuity.ai`
- **Region**: `ap-south-1`

## 📧 Email Addresses You Need

Make sure these email addresses exist and can receive emails:

1. **`noreply@mindacuity.ai`** - Sender email (needs verification in SES)
2. **`support@mindacuity.ai`** - Reply-to email (should exist for user replies)

## 🚀 Quick Test After Verification

Once verified, you can test with a simple email:

```python
from app.services.email_service import EmailService

email_service = EmailService()
result = await email_service.send_email(
    to_emails=["your-email@example.com"],
    subject="Test from MindAcuity",
    html_content="<h1>Test Email</h1><p>This is a test from MindAcuity!</p>"
)
print(result)
```

## ⚠️ Important Notes

1. **Sandbox Mode**: Until you get production access, you can only send to verified email addresses
2. **Rate Limits**: 
   - Sandbox: 200 emails/day, 1 email/second
   - Production: Higher limits after approval
3. **Bounce Rate**: Keep below 5%
4. **Complaint Rate**: Keep below 0.1%

## 🆘 If You Need Help

1. **Check AWS SES Console** for any error messages
2. **Verify your email** is actually receiving emails
3. **Check your spam folder** for the verification email
4. **Make sure you're in the right AWS region** (ap-south-1)

## 📞 Next Steps

1. ✅ Verify `noreply@mindacuity.ai` in AWS SES
2. ✅ Request production access
3. ✅ Test the email service
4. ✅ Set up domain verification (optional but recommended)
5. ✅ Configure SNS topics for bounce/complaint handling (optional)

Once you've verified your email, the test should pass! Let me know if you need help with any of these steps.
