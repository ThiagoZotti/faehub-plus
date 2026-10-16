import base64
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from zipfile import ZipFile

import backup_service as backup


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.secret=os.urandom(32)
        self.env=patch.dict(os.environ,FAEHUB_BACKUP_KEY=base64.urlsafe_b64encode(self.secret).decode())
        self.env.start();self.addCleanup(self.env.stop)

    def test_stream_encryption_roundtrip_and_existing_target_preserved(self):
        source=self.root/'school';encrypted=self.root/'backup';decoded=self.root/'restored'
        raw=b'school-data-private\x00'*100000;source.write_bytes(raw)
        backup.encrypt(source,encrypted,self.secret)
        self.assertNotIn(b'school-data-private',encrypted.read_bytes())
        backup.decrypt(encrypted,decoded,self.secret)
        self.assertEqual(decoded.read_bytes(),raw)
        with self.assertRaises(ValueError):backup.decrypt(encrypted,decoded,self.secret)
        self.assertEqual(decoded.read_bytes(),raw)

    def test_wrong_key_tampering_and_truncation_leave_no_plaintext(self):
        source=self.root/'source';source.write_bytes(b'private'*100)
        encrypted=self.root/'backup';backup.encrypt(source,encrypted,self.secret)
        original=encrypted.read_bytes()
        for raw,key in ((original,os.urandom(32)),(original[:-20],self.secret),(original[:50]+b'X'+original[51:],self.secret)):
            encrypted.write_bytes(raw);target=self.root/'decoded'
            with self.assertRaises(ValueError):backup.decrypt(encrypted,target,key)
            self.assertFalse(target.exists())

    def archive(self,checksum=None):
        dump=self.root/'database.dump';dump.write_bytes(b'PGDMP-disposable-fixture')
        bundle=self.root/'bundle.zip'
        with ZipFile(bundle,'w') as archive:
            archive.write(dump,'database.dump');archive.writestr('manifest.json',json.dumps(dict(format=1,sha256=checksum or backup.digest(dump),tables={'users':2})))
        path=self.root/'encrypted';backup.encrypt(bundle,path,self.secret)
        return path

    @patch('backup_service.run_pg',return_value=b'archive list')
    def test_manifest_authentication_and_checksum(self,run):
        path=self.archive()
        with backup.verified_backup(path,self.secret) as (dump,manifest):
            self.assertEqual(dump.read_bytes(),b'PGDMP-disposable-fixture')
            self.assertEqual(manifest['tables'],{'users':2})
        self.assertFalse(dump.exists());run.assert_called_once()

    @patch('backup_service.run_pg')
    def test_manifest_bad_checksum_rejected_before_pg_restore(self,run):
        path=self.archive('bad')
        with self.assertRaises(ValueError):
            with backup.verified_backup(path,self.secret):pass
        run.assert_not_called()

    def test_production_restore_and_repo_backup_are_refused(self):
        with self.assertRaisesRegex(ValueError,'produção'):
            backup.restore_to_empty('ignored','postgresql://user:other@host/db','postgresql://user:secret@host/db')
        with self.assertRaisesRegex(ValueError,'repositório'):
            backup.create_backup(Path(__file__).parent,'postgresql://invalid')

    @patch('backup_service.shutil.which',return_value='pg_dump')
    @patch('backup_service.subprocess.run')
    def test_no_credentials_in_process_arguments_or_errors(self,run,which):
        run.return_value=MagicMock(returncode=0,stdout=b'ok')
        backup.run_pg('pg_dump',['--format=custom'],'postgresql://user:secret@host/db')
        arguments=run.call_args.args[0]
        self.assertNotIn('secret',str(arguments));self.assertEqual('secret',run.call_args.kwargs['env']['PGPASSWORD'])
        self.assertEqual('db',run.call_args.kwargs['env']['PGDATABASE'])
        run.return_value.returncode=1
        with self.assertRaises(ValueError) as error:backup.run_pg('pg_dump',[],'postgresql://user:secret@host/db')
        self.assertNotIn('secret',str(error.exception))

    @patch('backup_service.urlopen')
    def test_drive_private_upload_checksum_and_no_retry(self,urlopen):
        path=self.root/'safe.fhbackup';path.write_bytes(b'encrypted-fixture')
        def response(payload,headers=None):
            mock=MagicMock();mock.__enter__.return_value=mock;mock.read.return_value=json.dumps(payload).encode();mock.headers=headers or {};return mock
        import hashlib
        urlopen.side_effect=[response({'access_token':'private-access'}),response({}, {'Location':'https://www.googleapis.com/upload/drive/v3/files?upload_id=private'}),
                             response({'id':'file-id','size':len(path.read_bytes()),'md5Checksum':hashlib.md5(path.read_bytes()).hexdigest()})]
        with patch.dict(os.environ,{f'FAEHUB_DRIVE_{key}':'private' for key in ('CLIENT_ID','CLIENT_SECRET','REFRESH_TOKEN','FOLDER_ID')}):
            self.assertEqual(backup.drive_upload(path),'file-id')
        self.assertEqual(urlopen.call_count,3)
        metadata=json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(metadata['parents'],['private']);self.assertNotIn('permissions',metadata)


if __name__=='__main__':unittest.main()
