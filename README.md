# CampusTrace — Lost and Found Management System

A web-based Lost and Found Management System that helps students report lost belongings, publish found-item listings, search for items, and submit claim requests through a centralized platform.

## 📌 Project Overview

CampusTrace is designed to make it easier for students to reconnect with their lost belongings within a campus environment. Instead of relying on scattered messages or manual announcements, users can report lost or found items and browse available listings through a single web application.

## ✨ Features

* **Report Lost Items:** Submit details about items that have been lost.
* **Report Found Items:** Create listings for items that have been found.
* **Browse Listings:** View lost and found item information.
* **Search Items:** Find relevant listings more easily.
* **Item Categories:** Organize items by categories such as mobile phones, earphones, and chargers.
* **Claim Requests:** Submit a request to claim an item.
* **Database Integration:** Store application data using SQLite.
* **Web Interface:** Access the application through a browser.

> Include only features that are implemented and working in your current code.

## 🛠️ Technologies Used

* **Backend:** Python, Flask
* **Frontend:** HTML, CSS, JavaScript
* **Database:** SQLite
* **Version Control:** Git and GitHub

## 📂 Project Structure

```text
CampusTrace/
├── lffapp.py
├── lost_found.db
└── README.md
```

* `lffapp.py` — Main Flask application.
* `lost_found.db` — SQLite database file, if used by the application.
* `README.md` — Project documentation.

The structure may change as the project develops.

## ⚙️ Installation and Setup

### Prerequisites

Install Python 3 and pip. Git is optional if you download the source code directly.

### 1. Clone the repository

```bash
git clone https://github.com/vishalchulke/CampusTrace.git
```

### 2. Open the project directory

```bash
cd CampusTrace
```

### 3. Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

Install Flask:

```bash
pip install Flask
```

If your application uses additional Python packages, install those too. Add a `requirements.txt` file to document all required dependencies.

### 5. Run the application

```bash
python lffapp.py
```

Open the local URL shown in your terminal. For a typical Flask development server, this is:

```text
http://127.0.0.1:5000/
```

## 🚀 How to Use

1. Start the Flask application.
2. Open the application in your browser.
3. Browse the available lost and found listings.
4. Submit a lost-item or found-item report.
5. Search listings by relevant details or categories.
6. Submit a claim request when the application provides that option.

The exact workflow depends on the features implemented in the current version.

## 🔒 Security and Privacy

* Do not publish passwords, secret keys, or personal information.
* Do not commit a database containing real users' personal data.
* Use environment variables for sensitive configuration.
* Validate user inputs and verify claim requests before handing over an item.

## 🔮 Future Enhancements

* User registration and secure authentication.
* Image uploads for lost and found items.
* Advanced search and category filters.
* Email notifications for matching items.
* Claim-status tracking.
* An administrator dashboard for managing listings.
* Deployment to a cloud hosting platform.

## 🎯 Project Objective

The goal of CampusTrace is to provide a simple and centralized digital solution for managing lost and found belongings in a campus environment.

## 👨‍💻 Author

**Vishal Chulke**

* GitHub: [vishalchulke](https://github.com/vishalchulke)

## 📄 License

This project is intended for educational and learning purposes. Add a license file if you intend to distribute the project under a specific open-source license.
