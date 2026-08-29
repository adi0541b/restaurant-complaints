# Gunakan PyMySQL sebagai pengganti mysqlclient jika terpasang -- PyMySQL murni
# Python (tidak perlu kompilasi/library sistem), jadi bisa diinstall tanpa akses
# root. Kalau PyMySQL belum diinstall (mis. saat memakai SQLite di lokal),
# baris ini dilewati saja tanpa error.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
