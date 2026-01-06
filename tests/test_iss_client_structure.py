import os
import unittest
from unittest.mock import MagicMock, patch
from lxml import etree
from app.services.issnet_client import IssNetClient

class TestIssNetClient(unittest.TestCase):

    @patch('app.services.issnet_client.pkcs12.load_key_and_certificates')
    @patch('builtins.open')
    @patch('os.getenv')
    def test_xml_generation_structure(self, mock_getenv, mock_open, mock_pkcs12):
        # Setup mocks
        mock_getenv.side_effect = lambda k, d=None: {
            "CERTIFICATE_PATH": "dummy.pfx",
            "CERTIFICATE_PASSWORD": "pass"
        }.get(k, d)

        # Mock certificate loading
        mock_private_key = MagicMock()
        mock_cert = MagicMock()
        mock_pkcs12.return_value = (mock_private_key, mock_cert, [])

        # Instantiate client
        client = IssNetClient()

        # Mock _sign_xml to return the element as is (simulating bypass of signature for structure check)
        # or simulate signed element by adding a dummy signature
        def mock_sign(element):
            sig = etree.SubElement(element, "Signature")
            sig.text = "DUMMY_SIGNATURE"
            return element

        client._sign_xml = mock_sign

        # Mock requests.post to avoid network call
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Return a dummy XML response
            mock_response.content = b"""
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <ConsultarNfseServicoPrestadoResponse xmlns="http://www.abrasf.org.br/nfse.xsd">
                        <ConsultarNfseServicoPrestadoResult>
                            <![CDATA[<ConsultarNfseServicoPrestadoResposta><ListaNfse><CompNfse><Nfse><InfNfse><Numero>123</Numero></InfNfse></Nfse></CompNfse></ListaNfse></ConsultarNfseServicoPrestadoResposta>]]>
                        </ConsultarNfseServicoPrestadoResult>
                    </ConsultarNfseServicoPrestadoResponse>
                </soap:Body>
            </soap:Envelope>
            """
            mock_post.return_value = mock_response

            result = client.consultar_notas_por_periodo("2023-01-01", "2023-01-31")

            # Verify request data structure
            # requests.post(url, data=..., ...)
            # call_args returns (args, kwargs)
            # args[0] is url (if positional) or might be keyword.
            # data is usually passed as 'data' keyword argument or positional.

            call_kwargs = mock_post.call_args.kwargs
            sent_xml = call_kwargs.get('data')

            # Basic checks on the sent XML
            self.assertIn("ConsultarNfseServicoPrestadoEnvio", sent_xml)
            self.assertIn("2023-01-01", sent_xml)
            self.assertIn("2023-01-31", sent_xml)
            self.assertIn("DUMMY_SIGNATURE", sent_xml)

            # Verify result parsing
            self.assertIn("ConsultarNfseServicoPrestadoResposta", result)
            self.assertIn("ListaNfse", result['ConsultarNfseServicoPrestadoResposta'])

if __name__ == '__main__':
    unittest.main()
