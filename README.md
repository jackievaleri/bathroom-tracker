# Bathroom Tracker App

This app tracks restroom usage with a simple interface. It logs button presses for each student and calculates restroom durations.

## Features

- Customizable buttons for student names.
- Logs button press times.
- Export data as a CSV file with restroom usage durations, either for today or all time.

## Deployment

This app is hosted on Heroku and uses SQLite for data storage.

## How to Use

Visit [https://bathroom-tracker-fae0cfed2e6e.herokuapp.com](https://bathroom-tracker-fae0cfed2e6e.herokuapp.com).

1. Press the button for your name when leaving the room.
2. Press it again when returning.
3. Download a CSV report for detailed usage logs.

Built with Flask, SQLite, and Heroku.

## Improvements

1. Multiplex for multiple classrooms.
2. More uniform or customizable color scheme.
