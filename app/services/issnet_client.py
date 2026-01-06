import os
import logging
from typing import Dict, Optional, Any, Union
import requests
import lxml.etree as etree
from signxml.signer import XMLSigner
from signxml import methods
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

class IssNetClient:
    """
    Cliente para integração com o WebService do ISS.net (Goiânia - ABRASF 2.04).
    Responsável pela construção de XML seguro, assinatura digital e comunicação SOAP.
    """

    # Namespaces requeridos pelo padrão ABRASF 2.04
    NS_MAP = {
        None: "http://www.abrasf.org.br/nfse.xsd",
        "ds": "http://www.w3.org/2000/09/xmldsig#"
    }

    # URL do endpoint de produção (Goiânia)
    ENDPOINT_URL = "https://nfse.issnetonline.com.br/abrasf204/goiania/nfse.asmx"

    def __init__(self):
        """
        Inicializa o cliente carregando as configurações e credenciais do ambiente.
        """
        self.certificate_path = os.getenv("CERTIFICATE_PATH")
        self.certificate_password = os.getenv("CERTIFICATE_PASSWORD")
        self.cnpj_prestador = os.getenv("CNPJ_PRESTADOR")
        self.im_prestador = os.getenv("IM_PRESTADOR")

        self.private_key = None
        self.certificate = None

        # Carrega as credenciais imediatamente na inicialização
        self._load_credentials()

    def _load_credentials(self):
        """
        Lê o arquivo .pfx (PKCS#12) e extrai a Chave Privada e o Certificado.
        Armazena-os em memória para uso nas assinaturas.
        """
        if not self.certificate_path or not self.certificate_password:
             logging.warning("Credenciais não configuradas totalmente (CERTIFICATE_PATH ou CERTIFICATE_PASSWORD ausentes).")
             return

        try:
            with open(self.certificate_path, "rb") as f:
                pfx_data = f.read()

            # Carrega a chave privada e o certificado usando cryptography
            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                pfx_data,
                self.certificate_password.encode("utf-8"),
                backend=default_backend()
            )
            self.private_key = private_key
            self.certificate = certificate
            logging.info("Credenciais e certificado carregados com sucesso.")

        except Exception as e:
            logging.error(f"Falha ao carregar credenciais: {e}")
            raise RuntimeError(f"Erro ao carregar certificado digital: {e}")

    def consultar_notas_por_periodo(self, start_date: str, end_date: str, page: int = 1) -> Dict[str, Any]:
        """
        Consulta as notas fiscais de serviço prestado por período.

        Args:
            start_date (str): Data inicial no formato AAAA-MM-DD.
            end_date (str): Data final no formato AAAA-MM-DD.
            page (int): Número da página para paginação.

        Returns:
            Dict[str, Any]: Dicionário contendo a resposta processada do serviço.
        """
        # Passo 1: Criar o elemento raiz do payload (ConsultarNfseServicoPrestadoEnvio)
        # Nota: Usamos lxml.etree.Element para construção orientada a objetos (seguro contra injeção)
        root = etree.Element("ConsultarNfseServicoPrestadoEnvio", nsmap=self.NS_MAP)

        # Passo 2: Construir a hierarquia do Pedido
        # O Pedido é o elemento que será assinado
        pedido = etree.Element("Pedido", nsmap=self.NS_MAP)

        # InfPedidoConsultarNfseServicoPrestado
        inf_pedido = etree.SubElement(pedido, "InfPedidoConsultarNfseServicoPrestado")
        # Id é obrigatório para referência da assinatura
        inf_pedido.set("Id", "pedido_consulta")

        # Prestador
        prestador = etree.SubElement(inf_pedido, "Prestador")
        cpf_cnpj = etree.SubElement(prestador, "CpfCnpj")
        cnpj = etree.SubElement(cpf_cnpj, "Cnpj")
        cnpj.text = self.cnpj_prestador

        if self.im_prestador:
            inscricao = etree.SubElement(prestador, "InscricaoMunicipal")
            inscricao.text = self.im_prestador

        # PeriodoCompetencia
        periodo = etree.SubElement(inf_pedido, "PeriodoCompetencia")
        dt_inicial = etree.SubElement(periodo, "DataInicial")
        dt_inicial.text = start_date
        dt_final = etree.SubElement(periodo, "DataFinal")
        dt_final.text = end_date

        # Pagina
        pagina_el = etree.SubElement(inf_pedido, "Pagina")
        pagina_el.text = str(page)

        # Passo 3: Assinar o XML
        # Assinamos o elemento 'Pedido', e a assinatura será inserida dentro dele (Enveloped)
        signed_pedido = self._sign_xml(pedido)

        # Adiciona o Pedido assinado ao elemento raiz
        root.append(signed_pedido)

        # Passo 4: Enviar a requisição SOAP
        return self._send_soap_request(root)

    def _sign_xml(self, element_to_sign: etree.Element) -> etree.Element:
        """
        Assina digitalmente um elemento XML usando XMLSigner.

        A assinatura é do tipo 'Enveloped' (a assinatura fica dentro do elemento assinado).
        Utiliza algoritmo RSA-SHA1 e Canonicalização C14N.

        Args:
            element_to_sign (etree.Element): O elemento XML a ser assinado.

        Returns:
            etree.Element: O elemento assinado contendo a tag <Signature>.
        """
        if not self.private_key or not self.certificate:
            raise RuntimeError("Tentativa de assinar XML sem credenciais carregadas.")

        # Configura o assinante (Signer)
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha1",
            digest_algorithm="sha1",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
        )

        # Prepara a chave e o certificado no formato PEM (bytes -> string)
        key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        cert_pem = self.certificate.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode("utf-8")

        # Realiza a assinatura
        # O método sign retorna uma cópia do elemento com a assinatura anexada
        signed_element = signer.sign(
            element_to_sign,
            key=key_pem,
            cert=cert_pem,
            always_add_key_value=True # Inclui X509Data/X509Certificate
        )

        return signed_element

    def _send_soap_request(self, payload_element: etree.Element) -> Dict[str, Any]:
        """
        Envelopa o payload XML em um Envelope SOAP e realiza o POST request.

        Args:
            payload_element (etree.Element): O payload XML (já assinado).

        Returns:
            Dict[str, Any]: A resposta parseada.
        """
        # Serializa o objeto XML payload para string sem declaração (já que vai dentro do envelope)
        payload_str = etree.tostring(payload_element, encoding="unicode", pretty_print=False)

        # Constrói o Envelope SOAP.
        # Aqui o uso de f-string é aceitável pois é apenas o wrapper externo padrão.
        # O conteúdo interno 'payload_str' foi gerado de forma segura via lxml.
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ConsultarNfseServicoPrestado xmlns="http://www.abrasf.org.br/nfse.xsd">
      <nfseCabecMsg><![CDATA[<?xml version="1.0" encoding="UTF-8"?><cabecalho versao="2.04" xmlns="http://www.abrasf.org.br/nfse.xsd"><versaoDados>2.04</versaoDados></cabecalho>]]></nfseCabecMsg>
      <nfseDadosMsg><![CDATA[{payload_str}]]></nfseDadosMsg>
    </ConsultarNfseServicoPrestado>
  </soap:Body>
</soap:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://www.abrasf.org.br/nfse.xsd/ConsultarNfseServicoPrestado"
        }

        try:
            # Realiza a requisição POST
            response = requests.post(
                self.ENDPOINT_URL,
                data=soap_envelope.encode('utf-8'), # Garante encoding correto
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            # Retorna a resposta parseada
            return self._parse_response(response.content)

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição SOAP: {e}")
            return {"error": str(e), "type": "NetworkError"}
        except Exception as e:
            logging.error(f"Erro inesperado no envio SOAP: {e}")
            return {"error": str(e), "type": "UnexpectedError"}

    def _parse_response(self, xml_content: bytes) -> Dict[str, Any]:
        """
        Parseia a resposta XML, removendo namespaces para facilitar o manuseio.

        Args:
            xml_content (bytes): O conteúdo bruto da resposta.

        Returns:
            Dict[str, Any]: Dicionário com os dados da resposta.
        """
        try:
            root = etree.fromstring(xml_content)

            # Remove namespaces de todos os elementos para simplificar o parsing
            # Utilizando root.iter() conforme recomendado
            for elem in root.iter():
                if not hasattr(elem.tag, 'find'): continue  # Pula comentários/PIs
                i = elem.tag.find('}')
                if i >= 0:
                    elem.tag = elem.tag[i+1:]

            # Busca o resultado específico da operação
            # O retorno geralmente está em ConsultarNfseServicoPrestadoResult
            result_node = root.find(".//ConsultarNfseServicoPrestadoResult")

            if result_node is not None and result_node.text:
                # O conteúdo dentro de Result geralmente é outro XML (string escapada ou CDATA)
                inner_xml = result_node.text
                inner_root = etree.fromstring(inner_xml.encode('utf-8'))

                # Novamente remove namespaces do XML interno
                for elem in inner_root.iter():
                    if not hasattr(elem.tag, 'find'): continue
                    i = elem.tag.find('}')
                    if i >= 0:
                        elem.tag = elem.tag[i+1:]

                return self._etree_to_dict(inner_root)

            # Caso não encontre o result esperado ou esteja vazio
            return {"raw_response": xml_content.decode('utf-8', errors='ignore')}

        except etree.XMLSyntaxError as e:
            logging.error(f"Erro de sintaxe XML na resposta: {e}")
            return {"error": "Invalid XML Response", "details": str(e)}
        except Exception as e:
            logging.error(f"Erro ao processar resposta: {e}")
            return {"error": "Processing Error", "details": str(e)}

    def _etree_to_dict(self, t: etree.Element) -> Dict[str, Any]:
        """
        Função auxiliar recursiva para converter lxml.etree.Element em dicionário Python.
        """
        d: Dict[str, Any] = {t.tag: {} if t.attrib else None}
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
            d[t.tag] = dd
        if t.attrib:
            d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                  d[t.tag]['#text'] = text
            else:
                d[t.tag] = text
        return d
