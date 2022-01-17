import logging


security_logger = logging.getLogger("gitmanager.security")

class SecurityLog:
    @staticmethod
    def _msg(request, action: str, status: str, msg: str) -> str:
        ip = request.META.get("REMOTE_ADDR")
        user = request.user if hasattr(request, "user") else None
        auth = request.auth if hasattr(request, "auth") else None
        return f"SECURITY {action} {status} {request.path} {ip} {user} {msg} {auth}"

    @staticmethod
    def reject(request, action, msg="", *args, **kwargs):
        return security_logger.info(SecurityLog._msg(request, action, "REJECTED", msg), *args, **kwargs)

    @staticmethod
    def accept(request, action, msg="", *args, **kwargs):
        return security_logger.info(SecurityLog._msg(request, action, "ACCEPTED", msg), *args, **kwargs)
