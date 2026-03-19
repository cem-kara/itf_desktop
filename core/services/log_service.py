"""
            "levels": levels_count
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if not line.strip():
                        continue
                    total_lines += 1

                    parsed_sonuc = LogService.parse_log_line(line)
                    parsed = parsed_sonuc.data if parsed_sonuc.data is not None else {}
                    level = parsed.get("level")
                    if isinstance(level, str) and level in levels_count:
                        levels_count[level] += 1
        except Exception as e:
            logger.error(f"Log özet hatası ({log_file_path}): {e}")

        return SonucYonetici.tamam(veri={
            "total_lines": total_lines,
            "levels": levels_count
        })
LogService — Log dosyalarını okuma ve filtreleme servisi

Sorumluluklar:
- Log dosyalarından kayıtları okuma
- Log seviyesine göre filtreleme
- Tarih aralığına göre filtreleme
- Metin araması
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Optional
from pathlib import Path
from core.hata_yonetici import SonucYonetici


from core.logger import logger, LOG_FILE, SYNC_LOG_FILE, ERROR_LOG_FILE, UI_LOG_FILE
from core.paths import LOG_DIR


class LogService:
    """Log dosyalarını okuma ve filtreleme servisi"""

    # Log seviye mapping
    LOG_LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    @staticmethod
    def get_available_log_files() -> SonucYonetici:
        """
        Mevcut log dosyalarını döndürür.
        
        Returns:
            List[Dict]: [{"name": "app.log", "path": "/full/path", "size_mb": 1.5}, ...]
        """
        log_files = []
        
        for log_file in Path(LOG_DIR).glob("*.log*"):
            try:
                size_bytes = os.path.getsize(log_file)
                size_mb = size_bytes / (1024 * 1024)
                
                log_files.append({
                    "name": log_file.name,
                    "path": str(log_file),
                    "size_mb": round(size_mb, 2),
                    "modified": datetime.fromtimestamp(os.path.getmtime(log_file)).strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                return SonucYonetici.hata(e, f"LogService.get_available_log_files ({log_file})")
                
        return SonucYonetici.tamam(veri=sorted(log_files, key=lambda x: x["name"]))

    @staticmethod
    def parse_log_line(line: str) -> SonucYonetici:
        """
        Bir log satırını parse eder.
        
        Format: 2026-02-28 10:30:45,123 - INFO - Message here
        
        Returns:
            Dict veya None: {"timestamp": "...", "level": "INFO", "message": "..."}
        """
        # Regex pattern: YYYY-MM-DD HH:MM:SS,mmm - LEVEL - Message
        pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - (\w+) - (.+)$'
        match = re.match(pattern, line.strip())
        
        if match: # SonucYonetici.data için dict döndür
            return SonucYonetici.tamam(veri={
                "timestamp": match.group(1),
                "level": match.group(2),
                "message": match.group(3),
                "raw": line.strip()
            })
        
        # Eğer parse edilemezse, raw olarak döndür # SonucYonetici.data için dict döndür
        return SonucYonetici.tamam(veri={
            "timestamp": "",
            "level": "",
            "message": line.strip(),
            "raw": line.strip()
        })

    @staticmethod
    def read_logs( # SonucYonetici.data için list[dict] döndür
        log_file_path: str,
        level_filter: Optional[str] = None,
        search_text: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_lines: int = 1000,
        reverse: bool = True
    ) -> SonucYonetici:
        """
        Log dosyasını okur ve filtreler.
        
        Args:
            log_file_path: Log dosyasının tam yolu
            level_filter: Log seviyesi filtresi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            search_text: Aranacak metin (case-insensitive)
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında)
            max_lines: Maksimum satır sayısı
            reverse: True ise en yeni loglar önce gelir
            
        Returns:
            List[Dict]: Parse edilmiş log kayıtları
        """
        if not os.path.exists(log_file_path):
            return SonucYonetici.hata(Exception(f"Log dosyası bulunamadı: {log_file_path}"), "LogService.read_logs")

        logs = []
        
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            # Reverse ise ters çevir (en yeni önce)
            if reverse:
                lines = reversed(lines)
                
            for line in lines:
                if len(logs) >= max_lines:
                    break
                    
                if not line.strip():
                    continue
                    
                parsed_sonuc = LogService.parse_log_line(line)
                if not parsed_sonuc.basarili:
                    logger.warning(f"Log satırı parse edilemedi: {line}")
                    continue
                
                parsed = parsed_sonuc.veri if parsed_sonuc.veri is not None else {}
                # Level filtresi
                if level_filter and parsed.get("level"):
                    if parsed.get("level") != level_filter:
                        continue
                if (start_date or end_date) and parsed.get("timestamp"):
                    try:
                        log_date = parsed["timestamp"].split()[0]  # YYYY-MM-DD
                        if start_date and log_date < start_date:
                            continue
                        if end_date and log_date > end_date:
                            continue
                    except Exception:
                        pass
                
                # Metin araması
                if search_text:
                    if search_text.lower() not in parsed["message"].lower():
                        continue
                
                logs.append(parsed)
                
        except Exception as e:
            return SonucYonetici.hata(e, f"LogService.read_logs ({log_file_path})")
            
        return SonucYonetici.tamam(veri=logs)

    @staticmethod
    def get_log_summary(log_file_path: str) -> SonucYonetici:
        """
        Log dosyasının özet istatistiklerini döndürür.
        
        Returns:
            Dict: {"total_lines": 1000, "levels": {"INFO": 500, "ERROR": 10, ...}}
        """
        if not os.path.exists(log_file_path):
            return SonucYonetici.tamam(veri={"total_lines": 0, "levels": {}})

        levels_count = {level: 0 for level in LogService.LOG_LEVELS.keys()}
        total_lines = 0
        
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if not line.strip():
                        continue
                    total_lines += 1

                    parsed_sonuc = LogService.parse_log_line(line)
                    parsed = parsed_sonuc.veri if parsed_sonuc.veri is not None else {}
                    level = parsed.get("level")
                    if isinstance(level, str) and level in levels_count:
                        levels_count[level] += 1
        except Exception as e:
            logger.error(f"Log özet hatası ({log_file_path}): {e}")

        return SonucYonetici.tamam(veri={
            "total_lines": total_lines,
            "levels": levels_count
        })
