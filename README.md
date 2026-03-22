# Restaurant Table Reservation System

A full-stack web application designed to streamline restaurant table bookings, handle user authentication, and provide administrators with a powerful dashboard for managing operations and viewing statistics.

## 🌟 Key Features

### For Users
* **Secure Authentication:** User registration, login, and profile management with password hashing (bcrypt).
* **Table Reservations:** Search for available tables by date, time, party size, and location (indoor/outdoor) without double-booking conflicts.
* **Timed Checkout:** A 2-minute expiration timer on pending reservations to prevent tied-up tables.
* **Payment Simulation:** Simulated checkout process confirming bookings with various payment methods.
* **Email Verification:** Account verification workflow to ensure valid user registration (simulation).
* **Booking History:** A dedicated dashboard to view all past and upcoming reservations.

### For Administrators
* **Admin Dashboard:** Centralized panel for staff to manage database records.
* **System Statistics:** View daily bookings, revenue stats, and table utilization directly from the admin panel.
* **Manage Reservations:** View, edit, or cancel customer reservations manually.
* **Manage Tables & Users:** Add/remove physical restaurant tables or manage registered user accounts.

## 🛠️ Built With

* **Backend:** Python, Flask server
* **Frontend:** HTML, CSS, JavaScript (Vanilla), Jinja2 Templating
* **Database:** MySQL
* **Security:** bcrypt (password hashing), Python UUIDs (for tokens)

## 📁 Project Structure

```text
restaurant_system/
├── static/                # CSS styling, Client-side JavaScript, Images
├── templates/             # HTML Templates (login, dashboard, admin, etc.)
├── app.py                 # Core Flask Backend Application / REST API
├── schema.sql             # MySQL database schema setup script
├── requirements.txt       # Python dependencies required to run the project
└── README.md              # Project documentation
