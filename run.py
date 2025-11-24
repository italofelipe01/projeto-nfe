from app import create_app

# Cria a aplicação usando a fábrica definida em app/__init__.py
app = create_app()

if __name__ == "__main__":
    # Roda o servidor Flask.
    app.run(debug=True)
