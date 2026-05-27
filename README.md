# Vehicle Service Booking System

A full-stack web application designed for a Database Management Systems (DBMS) mini-project. This system allows customers to register, manage multiple vehicles, and book service appointments. Administrators can manage the bookings, assign mechanics, and generate final invoices.

## Technology Stack

- **Frontend:** HTML5, Vanilla CSS (Glassmorphism UI), JavaScript (Fetch API)
- **Backend:** Node.js, Express.js
- **Database:** MongoDB (using Mongoose ODM)

## Features

### Customer Portal
- User Authentication (Registration & Login)
- Dashboard to manage profile and vehicles
- Add an unlimited number of vehicles to a profile
- Book a service by selecting a specific vehicle, service center, service type, and time slot
- Track the real-time status of service bookings
- Make payments for completed services

### Admin Portal (`/admin.html`)
- View a comprehensive list of all customer bookings
- Dynamically assign specialized Mechanics to pending bookings
- Update booking status (Pending -> Confirmed -> Completed)
- Automatically generate cost Invoices (including tax calculations) upon completion

## Installation & Setup

1. **Prerequisites:** 
   - Ensure you have [Node.js](https://nodejs.org/) installed.
   - Ensure you have [MongoDB](https://www.mongodb.com/try/download/community) installed and running locally on the default port `27017`.

2. **Install Dependencies:**
   Open a terminal in this directory and run:
   ```bash
   npm install
   ```

3. **Seed the Database:**
   To populate the database with initial Service Centers, Service Types, Mechanics, and Time Slots, run:
   ```bash
   node backend/seed.js
   ```

4. **Start the Server:**
   ```bash
   node backend/server.js
   ```
   *The server will start on port 5000.*

5. **Access the Application:**
   - **Customer UI:** Open your browser and go to `http://localhost:5000`
   - **Admin UI:** Open your browser and go to `http://localhost:5000/admin.html`
     *(When prompted, the Admin Password is: **admin123**)*

## Database Entities (MongoDB Collections)

Based on the original ER Diagram, the following collections are managed:
1. `customers`
2. `vehicles`
3. `servicecenters`
4. `servicetypes`
5. `mechanics`
6. `serviceslots`
7. `servicebookings`
8. `invoices`
9. `payments`
