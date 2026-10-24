import errno
import msvcrt
from contextlib import contextmanager
from pathlib import Path


class MonitorAlreadyRunningError(RuntimeError):
    pass


@contextmanager
def monitor_lock():
    project_folder = Path(__file__).resolve().parent.parent
    lock_folder = project_folder / "reports" / "locks"
    lock_folder.mkdir(parents=True, exist_ok=True)

    lock_path = lock_folder / "monitor.lock"
    lock_file = lock_path.open("a+b")
    acquired = False

    try:
        # Windows يحتاج بايتًا واحدًا على الأقل للقفل
        lock_file.seek(0, 2)

        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()

        lock_file.seek(0)

        try:
            msvcrt.locking(
                lock_file.fileno(),
                msvcrt.LK_NBLCK,
                1,
            )
            acquired = True

        except OSError as error:
            if error.errno in (
                errno.EACCES,
                errno.EAGAIN,
                errno.EDEADLK,
            ):
                raise MonitorAlreadyRunningError(
                    "Another monitor holds this project's lock."
                ) from error

            raise

        yield

    finally:
        try:
            if acquired:
                lock_file.seek(0)

                msvcrt.locking(
                    lock_file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
        finally:
            lock_file.close()


def main():
    try:
        with monitor_lock():
            print("LOCK ACQUIRED: This instance can run.")
            input("Keep this terminal open. Press Enter to release.")
            print("Lock released.")

        return 0

    except MonitorAlreadyRunningError:
        print("STOP: Another instance is already running.")
        return 1

    except OSError as error:
        print("STOP: Could not acquire or release lock:", error)
        return 1

    except KeyboardInterrupt:
        print("\nLock test stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())