# -*- coding: utf-8 -*-
"""RKE muayene utils."""


def envanter_durumunu_belirle(fiziksel: str, skopi: str) -> str:
    fiz_ok = (fiziksel == "Kullanima Uygun")
    sko_ok = (skopi in ("Kullanima Uygun", "Yapilmadi"))
    return "Kullanima Uygun" if fiz_ok and sko_ok else "Kullanima Uygun Degil"
