# Deploying EasyXASCalc

This guide explains how to deploy your EasyXASCalc web application to the internet so others can use it. We recommend using **Render.com** as it is free, easy to set up, and supports both Python and Node.js.

## Prerequisites

1. **GitHub Account**: You need to have your code pushed to a GitHub repository.
    * If you haven't done this, create a new repository on GitHub and push your `EasyXASCalc` folder to it.

## Deployment Steps on Render

1. **Sign Up/Log In**: Go to [render.com](https://render.com) and create an account (you can sign in with GitHub).
2. **New Web Service**:
    * Click the **"New +"** button and select **"Web Service"**.
    * Connect your GitHub repository (`EasyXASCalc`).
3. **Configure Service**:
    * **Name**: `easy-xas-calc` (or whatever you like).
    * **Region**: Choose the one closest to you (e.g., Oregon, Frankfurt).
    * **Branch**: `main` (or `master`).
    * **Root Directory**: Leave blank (it defaults to the repo root).
    * **Runtime**: **Python 3**.
    * **Build Command**: `./render-build.sh`
        * *This script (which I just created for you) builds the React frontend and installs Python dependencies.*
    * **Start Command**: `cd backend && gunicorn app:app`
4. **Create Web Service**:
    * Scroll down and click **"Create Web Service"**.
5. **Wait for Build**:
    * Render will start building your app. It will install Node.js modules, build the frontend, install Python libraries, and start the server.
    * This may take a few minutes.
6. **Done!**:
    * Once the build finishes, you will see a green **"Live"** badge.
    * You can access your app at the URL provided by Render (e.g., `https://easy-xas-calc.onrender.com`).

## Important Notes

* **Free Tier**: The free tier on Render spins down after 15 minutes of inactivity. The next time someone opens the link, it might take 30-60 seconds to "wake up". This is normal for free hosting.
* **Static Files**: The application is configured (`app.py`) to serve the compiled frontend (`frontend/dist`) as static files, so you don't need a separate frontend server.

## Troubleshooting

* If the build fails on `xraylib`, it might be due to missing system libraries. In that case, we might need a `Dockerfile`. But try the standard setup above first!
