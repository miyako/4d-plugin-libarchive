//%attributes = {"invisible":true,"preemptive":"capable"}
var $src : Text
var $archive : Text
var $status : Integer

$src:=Convert path system to POSIX(Get 4D folder(Current resources folder))+"test_folder"
$archive:="/tmp/4darchive_test.zip"

$status:=Archive Create($src; $archive; Archive format zip; Archive filter none)
ASSERT($status=0; "ZIP Create failed: "+String($status))

$status:=Archive Extract($archive; "/tmp/4darchive_zip_extract")
ASSERT($status=0; "ZIP Extract failed: "+String($status))
