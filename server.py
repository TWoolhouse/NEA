import time
import db
import network

Database = db.Database()

def main(repopulate=False):
    print("Server")
    # Repopulate the Database
    if repopulate:
        Database.new()
        with Database:
            Database.repopulate()
            # Test Accounts
            Database.register("Admin", "password")

    server = network.Server()

    with Database, server:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

if __name__ == "__main__":
    main(repopulate=True)