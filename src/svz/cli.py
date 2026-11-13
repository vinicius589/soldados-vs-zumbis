"""Inicialização, diagnóstico e registro de falhas da versão final."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def main() -> int:
    from .version import VERSION
    parser = argparse.ArgumentParser(description='Soldados vs Zumbis ' + VERSION)
    parser.add_argument('--self-test', metavar='RELATORIO', help='Verificar o pacote e gravar um diagnóstico JSON.')
    parser.add_argument('--headless', action='store_true', help='Usar drivers simulados durante o diagnóstico.')
    parser.add_argument('--resume-save', metavar='CAMPANHA', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.headless:
        os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', SVZ_RENDERER='software')
    if args.self_test and not (os.environ.get('SVZ_DATA_DIR') or os.environ.get('SVZ_SAVE_PATH')):
        os.environ['SVZ_DATA_DIR'] = str(Path(args.self_test).resolve().parent / 'diagnostic-data')
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    from .paths import data_dir
    directory = data_dir()
    try:
        from .data_migration import prepare_default_data
        migrated = prepare_default_data() if not args.self_test else []
        directory.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO, force=True, handlers=[RotatingFileHandler(directory / 'jogo.log', maxBytes=1024 * 1024, backupCount=2, encoding='utf-8')])
        logging.info('Inicializando Soldados vs Zumbis %s.', VERSION)
        if migrated:
            logging.info('Dados legados copiados, originais preservados: %s', ', '.join(migrated))
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
    except Exception as exc:
        logging.exception('Falha ao executar Soldados vs Zumbis.')
        if not args.self_test:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f'Não foi possível abrir o jogo.\n{exc}\nRegistro (se disponível):\n{directory / "jogo.log"}', 'Soldados vs Zumbis', 0x10)
        return 1
