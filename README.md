# FridgeInventory

FridgeInventory is a practical kitchen inventory app for tracking groceries, monitoring food freshness, and reducing waste at home.

It helps you keep an organized record of what you have in your fridge, pantry, or freezer, so you know what needs to be used soon and what might be close to expiring.

The app combines inventory tracking with AI-assisted item recognition and real-time notifications, making it easier to stay on top of what you have and when it should be used.

## Features

- Track groceries and household food items
- Store inventory data in the cloud with Firebase Firestore
- Add food items with details such as quantity and expiry date
- Use AI-powered scanning to identify food items
- Get notifications before food items expire
- Keep inventory available across devices through a web app
- Use web push notifications with service workers and VAPID

## How it works

Users can add food items to their inventory and record relevant details. The app stores this information in a database and keeps track of expiration dates. When an item is approaching expiry, the system sends an alert to the user so they can use it before it goes bad.

The app also includes AI-powered item recognition, which can help identify products quickly rather than requiring manual entry for every item.

## Tech stack

- Python with FastAPI
- Firebase Firestore for storage
- Google Gemini AI for item recognition
- Web Push notifications via VAPID and service workers
- Render for deployment

## Project structure

- `smart.py` — main FastAPI application and backend logic
- `database.py` — database and inventory logic
- `sw.js` — service worker for browser push notifications
- `render.yaml` — deployment configuration for Render
- `requirements.txt` — Python dependencies

## Notes

This project is designed to help households and individuals manage food more efficiently and reduce waste by making inventory and expiry tracking easier to maintain.
