#!/usr/bin/env python3
"""
Network Connectivity Fixer
Handles DNS resolution issues and network connectivity problems
"""

import socket
import requests
import time
import logging
from urllib.parse import urlparse
import subprocess
import platform

logger = logging.getLogger(__name__)

class NetworkFixer:
    def __init__(self):
        self.dns_servers = [
            '8.8.8.8',      # Google DNS
            '8.8.4.4',      # Google DNS
            '1.1.1.1',      # Cloudflare DNS
            '1.0.0.1',      # Cloudflare DNS
            '208.67.222.222', # OpenDNS
            '208.67.220.220'  # OpenDNS
        ]
        
    def test_connectivity(self, url: str) -> dict:
        """Test network connectivity to a URL"""
        result = {
            'url': url,
            'dns_resolution': False,
            'http_connectivity': False,
            'error': None,
            'suggestions': []
        }
        
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Test DNS resolution
            result['dns_resolution'] = self._test_dns_resolution(domain)
            
            if result['dns_resolution']:
                # Test HTTP connectivity
                result['http_connectivity'] = self._test_http_connectivity(url)
            else:
                result['error'] = f"DNS resolution failed for {domain}"
                result['suggestions'].append("Try using a different DNS server")
                result['suggestions'].append("Check your internet connection")
                
        except Exception as e:
            result['error'] = str(e)
            result['suggestions'].append("Check URL format")
            
        return result
    
    def _test_dns_resolution(self, domain: str) -> bool:
        """Test DNS resolution for a domain"""
        try:
            socket.gethostbyname(domain)
            return True
        except socket.gaierror as e:
            logger.warning(f"DNS resolution failed for {domain}: {e}")
            return False
    
    def _test_http_connectivity(self, url: str) -> bool:
        """Test HTTP connectivity to a URL"""
        try:
            response = requests.head(url, timeout=10)
            return response.status_code < 400
        except Exception as e:
            logger.warning(f"HTTP connectivity failed for {url}: {e}")
            return False
    
    def fix_dns_issues(self) -> dict:
        """Attempt to fix DNS issues"""
        fixes_applied = []
        
        # Test current DNS
        test_domain = "google.com"
        current_dns_works = self._test_dns_resolution(test_domain)
        
        if not current_dns_works:
            fixes_applied.append("Current DNS not working")
            
            # Try alternative DNS servers
            for dns_server in self.dns_servers:
                if self._test_dns_with_server(test_domain, dns_server):
                    fixes_applied.append(f"Alternative DNS {dns_server} works")
                    break
        
        return {
            'current_dns_working': current_dns_works,
            'fixes_applied': fixes_applied,
            'recommendations': self._get_dns_recommendations()
        }
    
    def _test_dns_with_server(self, domain: str, dns_server: str) -> bool:
        """Test DNS resolution with a specific DNS server"""
        try:
            # This is a simplified test - in practice, you'd need to
            # temporarily change system DNS settings
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            resolver.resolve(domain, 'A')
            return True
        except Exception:
            return False
    
    def _get_dns_recommendations(self) -> list:
        """Get DNS configuration recommendations"""
        system = platform.system().lower()
        
        if system == 'darwin':  # macOS
            return [
                "Try: sudo dscacheutil -flushcache",
                "Try: sudo killall -HUP mDNSResponder",
                "Change DNS in System Preferences > Network > Advanced > DNS"
            ]
        elif system == 'linux':
            return [
                "Try: sudo systemctl restart systemd-resolved",
                "Try: sudo service network-manager restart",
                "Edit /etc/resolv.conf to add nameserver 8.8.8.8"
            ]
        elif system == 'windows':
            return [
                "Try: ipconfig /flushdns",
                "Try: netsh winsock reset",
                "Change DNS in Network Settings"
            ]
        else:
            return ["Check your system's DNS configuration"]
    
    def get_working_urls(self, urls: list) -> dict:
        """Test multiple URLs and return which ones work"""
        results = {
            'working': [],
            'failing': [],
            'suggestions': []
        }
        
        for url in urls:
            test_result = self.test_connectivity(url)
            if test_result['dns_resolution'] and test_result['http_connectivity']:
                results['working'].append(url)
            else:
                results['failing'].append({
                    'url': url,
                    'error': test_result['error'],
                    'suggestions': test_result['suggestions']
                })
        
        if not results['working']:
            results['suggestions'].append("All URLs are failing - check your internet connection")
            results['suggestions'].append("Try using a VPN or different network")
        
        return results

# Example usage
if __name__ == "__main__":
    fixer = NetworkFixer()
    
    # Test connectivity
    test_urls = [
        "https://www.washingtonian.com/calendar-2/",
        "https://www.google.com",
        "https://www.github.com"
    ]
    
    print("Testing connectivity...")
    for url in test_urls:
        result = fixer.test_connectivity(url)
        print(f"{url}: {'✓' if result['dns_resolution'] and result['http_connectivity'] else '✗'}")
        if result['error']:
            print(f"  Error: {result['error']}")
    
    # Test DNS fixes
    print("\nTesting DNS fixes...")
    dns_result = fixer.fix_dns_issues()
    print(f"Current DNS working: {dns_result['current_dns_working']}")
    print(f"Fixes applied: {dns_result['fixes_applied']}")
    print(f"Recommendations: {dns_result['recommendations']}")
