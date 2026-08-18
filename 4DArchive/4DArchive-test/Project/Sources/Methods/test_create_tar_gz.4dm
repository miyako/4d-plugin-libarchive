//%attributes = {"invisible":true,"preemptive":"capable"}
var $src : Text
var $archive : Text
var $status : Integer

$src:=Convert path system to POSIX(Get 4D folder(Current resources folder))+"test_folder"
$archive:="/tmp/4darchive_test.tar.gz"

$status:=Archive Create($src; $archive; Archive format tar; Archive filter gzip)
ASSERT($status=0; "Archive Create failed: "+String($status))
