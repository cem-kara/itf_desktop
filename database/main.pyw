import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from database.sync_worker import SyncWorker


def on_finished():
    print("✅ Senkron başarıyla tamamlandı")
    app.quit()


def on_error(msg):
    print("❌ Senkron hatası:", msg)
    app.quit()


app = QApplication(sys.argv)

worker = SyncWorker()
worker.finished.connect(on_finished)
worker.error.connect(on_error)

worker.start()

# Güvenlik: 30 sn sonra zorla kapat
QTimer.singleShot(30000, app.quit)

sys.exit(app.exec())
