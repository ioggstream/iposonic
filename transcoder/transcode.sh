#!/bin/bash
# transcode.sh
# convert srcfile to dst format
# at maximum mbr bitrate

set -e

usage(){
	echo "usage: $0 srcfile dstformat mbr"
	echo ""
	echo "convert srcfile to dstformat using at max mbr"
	echo "output is directed to stdout"
} 

get_decoder(){
	[ $1 == "mp3" ] && echo "/usr/bin/mpg123 -q -w - ";
	[ $1 == "ogg" ] && echo "/usr/bin/ogg123 -q -w - ";
	return 0
}

get_encoder(){
	[ $1 == "mp3" ] && echo "/usr/bin/lame -S -b ";
	[ $1 == "ogg" ] && echo "/usr/bin/oggenc -Q - -o -  -M ";
	return 0
}


main(){
	local srcfile="$1"
	local dstformat="$2"
	local mbr="$3"

	echo >&2 "$0  $srcfile $2 $3"
	
	: ${srcfile?-} ${dstformat?-} ${mbr?-}
	
	srcext="${srcfile##*.}"
	
	if [ "$srcext" != "$dstformat" ]; then
		decoder=$(get_decoder $srcext)
	fi
	
	[ "$dstformat" == "ogg" ] && let mbr+=32
	
	encoder=$(get_encoder $dstformat)
	echo >&2 "decoder: $decoder"
	echo >&2 "srcfile: $srcfile"
        
	$decoder "$srcfile" | $encoder $mbr 
	
}

main "$@"

