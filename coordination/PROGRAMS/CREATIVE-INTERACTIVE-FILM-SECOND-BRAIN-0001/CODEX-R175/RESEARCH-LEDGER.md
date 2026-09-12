# R175 bounded research ledger

agent_id: `CODEX`

Scope: Windows confinement and publication semantics required by the R175
effective specification. This is engineering evidence, not independent review.

## Primary sources checked

- Microsoft Learn, **Reparse Point Operations**:
  https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-operations
- Microsoft Learn, **Reparse Points**:
  https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points
- Microsoft Learn, **CreateFile / FILE_FLAG_OPEN_REPARSE_POINT**:
  https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilea
- Microsoft Learn, **Locking and Unlocking Byte Ranges in Files**:
  https://learn.microsoft.com/en-us/windows/win32/fileio/locking-and-unlocking-byte-ranges-in-files
- Microsoft Learn, **Hard Links and Junctions**:
  https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions

## Findings mapped to implementation

1. A Windows junction is implemented with a reparse point. Path ancestry is
   therefore rejected when `FILE_ATTRIBUTE_REPARSE_POINT` is observable; tests
   create real save-directory and workspace junctions with `mklink /J`.
2. Opening a reparse point without the corresponding no-follow flag can operate
   on its target. R175 checks each lexical ancestor before file operations and
   fails closed on every detected reparse component.
3. Windows byte-range locks protect only the specified range, but the protected
   range may extend beyond the current end of file. R175 locks the supported
   positive range rather than only the current source length, preventing an
   append from landing immediately outside the lock.
4. Junctions and hard links have different identity semantics. Directory
   junctions are rejected as reparse ancestry; pre-existing multi-link target
   files are rejected, while create-only publication uses a temporary hard link
   and verifies the final target returns to link count one.

## Validation effects

- Added a Windows test proving a second handle cannot append beyond the current
  source EOF while migration publication is active.
- Preserved post-publication source byte and identity checks because mapped-file
  access is an explicit limitation of byte-range locks.
- Kept all research bounded to the local migration/public-safe surface. No
  external service, credential, private data, deployment or production path was
  accessed.

## Remaining unknowns

- Network shares and custom third-party filesystem filters are not claimed as
  supported. Ambiguous path or lock evidence fails closed.
- Executor clean reproduction is not an independent acceptance verdict.
