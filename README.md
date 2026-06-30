# Recent Files by Project | קבצים אחרונים לפי פרויקט

**עברית** · [English](#english)

ממשק מקומי ל-Windows שמציג קבצים שנוצרו לאחרונה במחשב — ממוין לפי תאריך ושיוך אוטומטי לפרויקטים.

## תכונות

- סריקת תיקיות פרויקטים, שולחן עבודה, הורדות ומסמכים
- מיון לפי תאריך יצירה / שינוי, פרויקט, שם וגודל
- סינון לפי פרויקט, סוג קובץ, שעה אחרונה, היום
- התראות Windows על קבצים חדשים (מעקב ברקע כל 2 דקות)
- ייצוא CSV ל-Excel
- System Tray עם תפריט קבצים אחרונים
- ווידג'ט Rainmeter לשולחן העבודה
- קובץ הגדרות לתיקיות מותאמות אישית

## התקנה

```bash
pip install -r requirements.txt
```

## הפעלה

| קובץ | תיאור |
|------|--------|
| `launch.bat` | שרת + דפדפן |
| `launch-tray.bat` | אייקון System Tray |

פתח: **http://localhost:8082/recent-files.html**

### Rainmeter

העתק את `rainmeter/RecentFiles.ini` ל:
`Documents\Rainmeter\Skins\RecentFiles\`

טען את הסקין ב-Rainmeter (דורש שרת פעיל על פורט 8082).

### סנכרון ל-GitHub

```powershell
.\sync-publish.ps1
```

## הגדרות

ערוך `recent_files_config.json` או השתמש בכפתור ⚙️ בממשק:

```json
{
  "extra_folders": ["C:\\path\\to\\folder"],
  "exclude_folders": ["node_modules"],
  "watch_interval_sec": 120,
  "notify_windows": true
}
```

## ארכיטקטורה

- `recent_files_server.py` — שרת HTTP + סריקה + API
- `recent-files.html` — ממשק משתמש (RTL עברית)
- `recent_files_tray.pyw` — System Tray
- `recent_files_config.json` — הגדרות

### API

| Endpoint | תיאור |
|----------|--------|
| `GET /api/files?days=30&limit=500&refresh=1` | רשימת קבצים |
| `GET /api/config` | קריאת הגדרות |
| `POST /api/config` | שמירת הגדרות |
| `GET /api/open?mode=file&path=...` | פתיחת קובץ |

## מפתח

**David Patlas** — [DavidPatlas-AI](https://github.com/DavidPatlas-AI)

---

## English

Local Windows dashboard that lists recently created files on your PC, sorted by date/time and automatically mapped to project folders.

### Features

- Scans project folders, Desktop, Downloads, Documents
- Filter by project, file type, last hour, today
- Windows toast notifications for new files
- CSV export for Excel
- System Tray icon with recent-files submenu
- JSON config for custom folders

### Quick start

```bash
pip install -r requirements.txt
launch.bat
```

Open **http://localhost:8082/recent-files.html**

MIT License