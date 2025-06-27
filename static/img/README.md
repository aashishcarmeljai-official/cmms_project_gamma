# PWA Icons Directory

This directory contains the Progressive Web App (PWA) icons required for the CMMS Mobile application.

## Required Icons

The following icon files are referenced in the PWA manifest and should be created:

### Main App Icons
- `icon-72x72.png` - 72x72 pixels
- `icon-96x96.png` - 96x96 pixels  
- `icon-128x128.png` - 128x128 pixels
- `icon-144x144.png` - 144x144 pixels
- `icon-152x152.png` - 152x152 pixels
- `icon-192x192.png` - 192x192 pixels
- `icon-384x384.png` - 384x384 pixels
- `icon-512x512.png` - 512x512 pixels

### Apple Touch Icons
- `icon-152x152.png` - 152x152 pixels (iPhone)
- `icon-167x167.png` - 167x167 pixels (iPad)
- `icon-180x180.png` - 180x180 pixels (iPhone 6 Plus)

### Favicon
- `favicon-16x16.png` - 16x16 pixels
- `favicon-32x32.png` - 32x32 pixels

### Screenshots (Optional)
- `screenshot-mobile-1.png` - 390x844 pixels (Dashboard)
- `screenshot-mobile-2.png` - 390x844 pixels (Task Detail)

## Icon Design Guidelines

- **Style**: Flat design with rounded corners
- **Colors**: Primary blue (#007bff) with white background
- **Symbol**: Tools/wrench icon representing CMMS
- **Format**: PNG with transparency support
- **Purpose**: Both "any" and "maskable" for PWA compatibility

## Temporary Solution

Until proper icons are created, the PWA will use default browser icons. The mobile interface will still function fully without these icons.

## Generation Tools

Icons can be generated using:
- Online PWA icon generators
- Design tools like Figma, Sketch, or Adobe Illustrator
- Command-line tools like ImageMagick
- AI-powered icon generators

## Implementation Notes

- Icons are referenced in `static/manifest.json`
- Apple touch icons are linked in mobile templates
- Favicon is used for browser tabs
- Screenshots appear in app store listings 