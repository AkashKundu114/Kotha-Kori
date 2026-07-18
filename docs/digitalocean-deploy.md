# DigitalOcean Deployment

Target domain: `aisathi.app`

Production webhook: `https://aisathi.app/webhook/whatsapp`

WhatsApp deep link: `https://wa.me/<WA_PUBLIC_PHONE_NUMBER>`

## Droplet Setup

1. Create an Ubuntu LTS Droplet.
2. Point these DNS records at the Droplet IPv4 address:
   - `A aisathi.app`
   - `A www.aisathi.app`
3. Install Docker and the Compose plugin.
4. Copy the repository to the Droplet.
5. Create `.env` from `.env.example` and fill every required value.
6. Start production services:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Meta WhatsApp Setup

Set the callback URL in Meta Developer Console to:

```text
https://aisathi.app/webhook/whatsapp
```

Set the verify token to the same value as:

```text
WA_WEBHOOK_VERIFY_TOKEN
```

Subscribe the WhatsApp product to message webhooks. Use the phone number configured in `WA_PUBLIC_PHONE_NUMBER` for the public `wa.me` link.

## DigitalOcean Spaces

Create a Spaces bucket and set:

```text
S3_BUCKET=aisathi-assets
AWS_REGION=blr1
S3_ENDPOINT_URL=https://blr1.digitaloceanspaces.com
AWS_ACCESS_KEY_ID=<spaces-key>
AWS_SECRET_ACCESS_KEY=<spaces-secret>
```

## Health Checks

```bash
curl https://aisathi.app/health
curl https://aisathi.app/
```

The root endpoint returns the webhook URL and WhatsApp link metadata.
