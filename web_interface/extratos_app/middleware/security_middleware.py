"""
Middleware de segurança personalizado
"""
import time
import logging
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    """Middleware para aplicar controles de segurança"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Processar requisição para aplicar controles de segurança"""
        
        # Rate limiting básico por IP
        if hasattr(settings, 'RATELIMIT_ENABLE') and settings.RATELIMIT_ENABLE:
            if self._is_rate_limited(request):
                logger.warning(f"Rate limit excedido para IP: {self._get_client_ip(request)}")
                return HttpResponseForbidden("Rate limit excedido. Tente novamente em alguns minutos.")
        
        # Registrar informações da requisição
        self._log_request_info(request)
        
        return None
    
    def _is_rate_limited(self, request):
        """Verifica se o IP está com rate limit"""
        client_ip = self._get_client_ip(request)
        cache_key = f"rate_limit_{client_ip}"
        
        # Limites por endpoint
        limits = {
            '/processar/': {'requests': 10, 'window': 600},  # 10 requests por 10 minutos
            '/': {'requests': 50, 'window': 300},  # 50 requests por 5 minutos
            'default': {'requests': 100, 'window': 300}  # 100 requests por 5 minutos
        }
        
        # Determinar limite baseado no path
        path = request.path
        limit_config = limits.get(path, limits['default'])
        
        # Verificar cache
        request_times = cache.get(cache_key, [])
        now = time.time()
        
        # Remover requests antigas
        window_start = now - limit_config['window']
        request_times = [t for t in request_times if t > window_start]
        
        # Verificar se excedeu o limite
        if len(request_times) >= limit_config['requests']:
            return True
        
        # Adicionar nova requisição
        request_times.append(now)
        cache.set(cache_key, request_times, limit_config['window'])
        
        return False
    
    def _get_client_ip(self, request):
        """Obter IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _log_request_info(self, request):
        """Registrar informações da requisição"""
        if request.path in ['/processar/', '/']:
            logger.info(f"Requisição: {request.method} {request.path} - IP: {self._get_client_ip(request)} - UA: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")

class FileUploadSecurityMiddleware(MiddlewareMixin):
    """Middleware para segurança de upload de arquivos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Processar upload de arquivos"""
        
        if request.method == 'POST' and request.FILES:
            # Verificar tamanho total dos arquivos
            total_size = sum(f.size for f in request.FILES.values())
            max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)  # 50MB
            
            if total_size > max_size:
                logger.warning(f"Upload muito grande: {total_size} bytes de {self._get_client_ip(request)}")
                return HttpResponseForbidden("Tamanho total dos arquivos excede o limite permitido.")
            
            # Verificar número de arquivos
            if len(request.FILES) > 20:  # Máximo 20 arquivos
                logger.warning(f"Muitos arquivos no upload: {len(request.FILES)} de {self._get_client_ip(request)}")
                return HttpResponseForbidden("Número de arquivos excede o limite permitido.")
        
        return None
    
    def _get_client_ip(self, request):
        """Obter IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class HeaderSecurityMiddleware(MiddlewareMixin):
    """Middleware para adicionar cabeçalhos de segurança"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_response(self, request, response):
        """Adicionar cabeçalhos de segurança"""
        
        # Remover cabeçalhos que podem vazar informações
        if 'Server' in response:
            del response['Server']
        
        # Adicionar cabeçalhos de segurança
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy
        if not response.get('Content-Security-Policy'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data:; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none';"
            )
            response['Content-Security-Policy'] = csp
        
        return response
