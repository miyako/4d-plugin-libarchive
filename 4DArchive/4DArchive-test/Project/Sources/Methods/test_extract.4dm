//%attributes = {"invisible":true,"preemptive":"capable"}
var $archive : Text
var $dest : Text
var $status : Integer

$archive:="/tmp/4darchive_test.tar.gz"
$dest:="/tmp/4darchive_extract_test"

$status:=Archive Extract($archive; $dest)
ASSERT($status=0; "Archive Extract failed: "+String($status))
