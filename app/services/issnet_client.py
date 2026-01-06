import os
import requests
from lxml import etree
from signxml import XMLSigner, XMLVerifier, methods
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class IssNetClient:
    """
    Client for ISS.net WebService (ABRASF 2.04) for Goiânia.
    Handles XML construction, digital signature (DSig), and SOAP communication.
    """

    # Namespaces required by ABRASF 2.04
    NSMAP = {
        None: "http://www.abrasf.org.br/nfse.xsd",
        "ds": "http://www.w3.org/2000/09/xmldsig#",
    }

    # Endpoint for Goiânia (Production)
    # Note: Using the URL provided in specs.
    ENDPOINT = "https://nfse.issnetonline.com.br/abrasf204/goiania/nfse.asmx"

    def __init__(self):
        """
        Initializes the client by loading the digital certificate from configuration.
        """
        self.cert_path = os.getenv("CERTIFICATE_PATH")
        self.cert_pass = os.getenv("CERTIFICATE_PASSWORD")

        if not self.cert_path or not self.cert_pass:
            # We log a warning but don't crash yet, allowing instantiation for testing purposes
            print("Warning: CERTIFICATE_PATH or CERTIFICATE_PASSWORD not set.")
            self.private_key = None
            self.certificate = None
        else:
            self._load_certificate()

    def _load_certificate(self):
        """
        Loads the PKCS#12 (.pfx) certificate.
        Extracts the private key and the certificate object.
        """
        try:
            with open(self.cert_path, "rb") as f:
                pfx_data = f.read()

            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                pfx_data,
                self.cert_pass.encode("utf-8"),
                backend=default_backend()
            )
            self.private_key = private_key
            self.certificate = certificate
        except Exception as e:
            raise RuntimeError(f"Failed to load certificate: {e}")

    def _sign_xml(self, element_to_sign):
        """
        Digitally signs the XML element using signxml.
        It appends the Signature tag to the element.

        Args:
            element_to_sign (lxml.etree.Element): The element to be signed (typically the Pedido).

        Returns:
            lxml.etree.Element: The signed XML element (with <Signature> appended).
        """
        if not self.private_key or not self.certificate:
            raise RuntimeError("Cannot sign XML: Certificate not loaded.")

        # Using signxml to sign.
        # We use 'enveloped' method to place Signature inside the element.
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha1",
            digest_algorithm="sha1",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
        )

        # Convert certificate to PEM for signxml
        cert_pem = self.certificate.public_bytes(encoding=serialization.Encoding.PEM)
        key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )

        signed_element = signer.sign(
            element_to_sign,
            key=key_pem,
            cert=cert_pem,
            always_add_key_value=True
        )

        return signed_element

    def consultar_notas_por_periodo(self, start_date, end_date, page=1):
        """
        Queries service notes by period (ConsultarNfseServicoPrestado).

        Args:
            start_date (str): Start date in YYYY-MM-DD.
            end_date (str): End date in YYYY-MM-DD.
            page (int): Page number.

        Returns:
            dict: Parsed response.
        """
        # 1. Build the XML Payload Components

        # Root Env (will contain the signed Pedido)
        envio = etree.Element("ConsultarNfseServicoPrestadoEnvio", nsmap=self.NSMAP)

        # Pedido (to be signed)
        # Note: We create it standalone first to sign it, then we will attach it to envio?
        # Or we create it, sign it, and signxml returns the signed object which we attach.
        # However, ABRASF uses namespaces. We should be careful with namespace inheritance.

        pedido = etree.Element("Pedido", nsmap=self.NSMAP)

        # InfPedido
        inf_pedido = etree.SubElement(pedido, "InfPedidoConsultarNfseServicoPrestado")
        inf_pedido.set("Id", "pedido_consulta_1")

        prestador = etree.SubElement(inf_pedido, "Prestador")
        cpf_cnpj = etree.SubElement(prestador, "CpfCnpj")
        cnpj_elem = etree.SubElement(cpf_cnpj, "Cnpj")
        cnpj_elem.text = os.getenv("CNPJ_PRESTADOR", "00000000000000")

        inscricao = etree.SubElement(prestador, "InscricaoMunicipal")
        inscricao.text = os.getenv("IM_PRESTADOR", "000000")

        # PeriodoCompetencia
        periodo = etree.SubElement(inf_pedido, "PeriodoCompetencia")
        data_inicial = etree.SubElement(periodo, "DataInicial")
        data_inicial.text = start_date
        data_final = etree.SubElement(periodo, "DataFinal")
        data_final.text = end_date

        # Pagina
        pagina = etree.SubElement(inf_pedido, "Pagina")
        pagina.text = str(page)

        # 2. Sign the Pedido
        try:
            if self.private_key:
                # Sign the Pedido element.
                # The result will be a new Pedido element containing the Signature.
                signed_pedido = self._sign_xml(pedido)

                # Append the signed pedido to the Envio
                envio.append(signed_pedido)

                xml_str = etree.tostring(envio, encoding="utf-8").decode("utf-8")
            else:
                # Fallback for no cert (dev mode without cert)
                envio.append(pedido)
                xml_str = etree.tostring(envio, encoding="utf-8").decode("utf-8")
        except Exception as e:
            print(f"Signing failed: {e}")
            # Ensure we still have a structure even if signing fails, for debugging
            if len(envio) == 0:
                envio.append(pedido)
            xml_str = etree.tostring(envio, encoding="utf-8").decode("utf-8")

        # 3. Wrap in SOAP Envelope
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ConsultarNfseServicoPrestado xmlns="http://www.abrasf.org.br/nfse.xsd">
      <nfseCabecMsg><![CDATA[<?xml version="1.0" encoding="UTF-8"?><cabecalho versao="2.04" xmlns="http://www.abrasf.org.br/nfse.xsd"><versaoDados>2.04</versaoDados></cabecalho>]]></nfseCabecMsg>
      <nfseDadosMsg><![CDATA[{xml_str}]]></nfseDadosMsg>
    </ConsultarNfseServicoPrestado>
  </soap:Body>
</soap:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://www.abrasf.org.br/nfse.xsd/ConsultarNfseServicoPrestado"
        }

        # 4. Send Request
        try:
            response = requests.post(self.ENDPOINT, data=soap_envelope, headers=headers, timeout=30)
            response.raise_for_status()
            return self._parse_response(response.content)
        except requests.exceptions.RequestException as e:
            return {"error": f"HTTP Error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected Error: {str(e)}"}

    def _parse_response(self, content):
        """
        Parses the SOAP response.
        """
        try:
            # Parse SOAP Envelope
            root = etree.fromstring(content)

            # Simple search for the result tag
            result_element = root.find(".//{http://www.abrasf.org.br/nfse.xsd}ConsultarNfseServicoPrestadoResult")
            if result_element is None:
                # Try without namespace or check localname
                for elem in root.iter():
                    if "ConsultarNfseServicoPrestadoResult" in elem.tag:
                        result_element = elem
                        break

            if result_element is not None and result_element.text:
                inner_xml = result_element.text
                inner_root = etree.fromstring(inner_xml.encode('utf-8'))
                return self._etree_to_dict(inner_root)

            return {"raw_response": content.decode('utf-8')}

        except Exception as e:
            return {"error": f"Parsing Error: {str(e)}", "raw": content.decode('utf-8')}

    def _etree_to_dict(self, t):
        """Helper to convert etree to dict."""
        d = {t.tag.split('}')[-1]: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = {}
            for dc in map(self._etree_to_dict, children):
                for k, v in dc.items():
                    if k in dd:
                        if not isinstance(dd[k], list):
                            dd[k] = [dd[k]]
                        dd[k].append(v)
                    else:
                        dd[k] = v
            d = {t.tag.split('}')[-1]: dd}
        if t.attrib:
            d[t.tag.split('}')[-1]].update(('@' + k, v) for k, v in t.attrib.items())
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                  d[t.tag.split('}')[-1]]['#text'] = text
            else:
                d[t.tag.split('}')[-1]] = text
        return d
