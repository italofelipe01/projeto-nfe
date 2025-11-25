from app import create_app

# Cria a aplicação usando a fábrica definida em app/__init__.py
app = create_app()

if __name__ == "__main__":
    # Roda o servidor Flask.
    # A opção `use_reloader=False` é essencial para impedir que o watchdog
    # do Flask reinicie o servidor enquanto o robô RPA (Playwright) está em
    # execução. O reinício abrupto causa o erro "EPIPE: broken pipe",
    # pois o processo principal que iniciou o robô é encerrado.
    app.run(debug=True, use_reloader=False)
