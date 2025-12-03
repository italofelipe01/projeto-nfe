
import pandas as pd
import pytest
from app.converter import process_conversion
import os

# Mock the callback
def mock_callback(task_id, status, progress, msg, details, **kwargs):
    pass

def test_duplicate_detection_with_whitespace(tmp_path):
    """
    Test case to verify that duplicate detection works correctly even when
    there are leading/trailing whitespaces in key columns (Document Number and CNPJ).
    """
    # Create a CSV file with two rows that differ only by whitespace in the key columns
    columns = [
        "modelo", "numero nf", "valor total", "cnpj", "data emissao", "valor tributavel", "aliquota",
        "data pagamento", "razao social", "im prestador", "iss retido", "cep",
        "endereco prestador", "numero", "bairro", "cidade", "uf", "ddd",
        "tributado no municipio", "item lc", "unidade economica"
    ]

    # Valid row data base (using 9999 for item lc to avoid confusion with doc number 123)
    row_base = "01/01/2023;Test;12345;Nao;12345678;Rua Teste;10;Centro;Goiania;GO;62;Sim;9999;Sim"

    data = f"{';'.join(columns)}\n"
    # Row 1: " 123 " (Duplicate A)
    data += f"55; 123 ;100,00;00.000.000/0001-91;01/01/2023;100,00;5;{row_base}\n"
    # Row 2: "123" (Duplicate A)
    data += f"55;123;100,00;00.000.000/0001-91;01/01/2023;100,00;5;{row_base}\n"
    # Row 3: "888" (Unique - Valid)
    data += f"55;888;100,00;00.000.000/0001-91;01/01/2023;100,00;5;{row_base}\n"

    file_path = tmp_path / "test_duplicates.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)

    form_data = {
        "inscricao_municipal": "123456",
        "mes": "01",
        "ano": "2023",
        "razao_social": "Test Company",
        "codigo_servico": "1234",
        "separador_decimal": "virgula",
        "digito_verificador": "nao"
    }

    # Mock config download dir for this test
    from app.config import Config
    original_downloads_dir = Config.DOWNLOADS_DIR
    Config.DOWNLOADS_DIR = str(tmp_path)

    task_id = "test_task"

    try:
        process_conversion(task_id, str(file_path), form_data, mock_callback)
    except Exception:
        # We don't expect an exception here because we have 1 valid row (Row 3).
        # If success_count == 0, an exception would be raised.
        pass
    finally:
        # Restore config
        Config.DOWNLOADS_DIR = original_downloads_dir

    # Expectation:
    # 1. Conversion file generated (containing only the Unique row "888")
    # 2. Error report generated (containing errors for rows 1 and 2)

    # Check 1: Conversion File
    files = list(tmp_path.glob("conversao_*.txt"))
    assert len(files) == 1, "Conversion file should be generated for the valid row"

    with open(files[0], "r") as f:
        lines = f.readlines()

    # Header + 1 valid line = 2 lines
    assert len(lines) == 2, f"Expected 2 lines (Header + 1 Valid), got {len(lines)}"

    # Verify content: Doc number 888 should be present
    fields = lines[1].strip().split(";")
    doc_num = fields[1]
    assert doc_num == "888", f"Expected doc number 888, got {doc_num}"

    # Check 2: Error Report
    error_files = list(tmp_path.glob("erros_*.txt"))
    assert len(error_files) == 1, "Error report should be generated for duplicates"

    with open(error_files[0], "r") as f:
        content = f.read()

    # Verify duplicate error message
    assert "Erro de Duplicidade" in content, "Error report missing duplicate error message"
    # Verify both duplicates (Row 1 and Row 2 in input file) are reported.
    # Note: Logic usually maps file line 1 to Row 2 (since header is 1).
    assert "LINHA 2" in content
    assert "LINHA 3" in content
