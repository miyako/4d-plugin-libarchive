//%attributes = {"invisible":true,"preemptive":"capable"}
var $archive : Text
var $json : Text

$archive:="/tmp/4darchive_test.tar.gz"
$json:=Archive List($archive)
ASSERT(Length($json)>2; "Archive List returned empty: "+$json)
