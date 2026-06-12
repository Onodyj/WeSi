#!/usr/bin/env python3
"""
SiteIQ startup script.
Usage: python run_siteiq.py [--host HOST] [--port PORT] [--debug]
"""
import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('siteiq')


def main():
    parser = argparse.ArgumentParser(description='Run the SiteIQ web server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    # Load .env if present
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        logger.info('Loading environment from .env')
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    os.environ.setdefault(key.strip(), val.strip())

    try:
        from we_si.app import create_app
    except ImportError as e:
        logger.error('Failed to import SiteIQ app: %s', e)
        logger.error('Make sure dependencies are installed: pip install -r requirements.txt')
        sys.exit(1)

    app = create_app()
    logger.info('Starting SiteIQ on http://%s:%d', args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug or os.getenv('FLASK_DEBUG', '').lower() == 'true')


if __name__ == '__main__':
    main()
