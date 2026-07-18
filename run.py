import os
import threading
import webbrowser
from app import create_app, db, seed

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed()

    port = int(os.environ.get('PORT', 5000))
    url = f'http://localhost:{port}'
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print(f"\nFarm Management System running at {url}")
    print("Press Ctrl+C to stop the server.\n")
    app.run(debug=False, port=port)
