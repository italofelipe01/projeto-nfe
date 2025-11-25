# -*- coding: utf-8 -*-
"""
Módulo de Tratamento de Erros (rpa/error_handler.py).

Responsabilidade:
1. Definir a hierarquia de exceções personalizadas.
2. Permitir que o controlador distinga erros de infraestrutura de regras de negócio.
"""


class RPAError(Exception):
    """
    Classe base para todas as exceções do Robô ISS.net.
    Captura a mensagem e, opcionalmente, a exceção original (chaining).
    """

    def __init__(self, message, original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception


class AuthenticationError(RPAError):
    """
    Levantado quando há falha no login.
    Ex: Senha incorreta, falha na leitura do teclado virtual.
    Ação recomendada: Não tentar novamente sem intervenção humana.
    """

    pass


class CredentialError(AuthenticationError):
    """
    Subclasse para erros específicos de credenciais não encontradas ou inválidas.
    """
    pass


class NavigationError(RPAError):
    """
    Levantado quando o robô não encontra um elemento esperado durante a navegação.
    Ex: O menu mudou, timeout ao esperar o grid de empresas, URL incorreta.
    Ação recomendada: Pode valer a pena uma re-tentativa (retry).
    """

    pass


class ProcessingError(RPAError):
    """
    Levantado quando o upload falha ou o portal rejeita o arquivo explicitamente.
    Ex: Arquivo inválido, CNPJ não cadastrado, validação de negócio falhou.
    Ação recomendada: Registrar erro e notificar usuário final.
    """

    pass


class PortalOfflineError(RPAError):
    """
    Levantado quando o site está inacessível, lento demais ou retornando erro 500.
    Ação recomendada: Pausar execução e tentar mais tarde (backoff).
    """

    pass
