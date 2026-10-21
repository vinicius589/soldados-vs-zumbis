"""Inicialização, diagnóstico e registro de falhas da versão final."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os


def main() -> int:
    from .version import VERSION
    parser = argparse.ArgumentParser(description='Soldados vs Zumbis ' + VERSION)
    parser.add_argument('--self-test', metavar='RELATORIO', help='Verificar o pacote e gravar um diagnóstico JSON.')
    parser.add_argument('--headless', action='store_true', help='Usar drivers simulados durante o diagnóstico.')
    parser.add_argument('--resume-save', metavar='CAMPANHA', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.headless:
        os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', SVZ_RENDERER='software')
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    from .paths import data_dir
    directory = data_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO, force=True, handlers=[RotatingFileHandler(directory / 'jogo.log', maxBytes=1024 * 1024, backupCount=2, encoding='utf-8')])
        logging.info('Inicializando Soldados vs Zumbis %s.', VERSION)
        if args.self_test:
            from .diagnostics import verify, verify_resume
            if args.resume_save:
                verify_resume(args.self_test, args.resume_save)
            else:
                verify(args.self_test)
        else:
            from .app import Game
            Game().run()
        return 0
    except Exception:
        logging.exception('Falha ao executar Soldados vs Zumbis.')
        if not args.self_test:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f'Não foi possível abrir o jogo.\nConsulte o registro em:\n{directory / "jogo.log"}', 'Soldados vs Zumbis', 0x10)
        return 1
