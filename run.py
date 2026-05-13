from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True allows the server to auto-reload when you save files
    app.run(debug=True)