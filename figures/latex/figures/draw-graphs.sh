#!/bin/bash

function crop {
    pdfcrop "${1}.pdf"
    mv "${1}-crop.pdf" "${1}.pdf"
}

chart="_n225-2016-06-20.csv"
if [ ! -f "$chart" ]
then
    cat "_n225.csv" \
        | awk 'BEGIN { FS=","; OFS="," } /2016-06-20T0[0-5]/ || /2016-06-20T06:00/ { if ($8 != "") print $1, $3, $8 }' \
    > $chart
fi

font="Fira Sans Light"
# font="HelveticaNeueLTStd-Light"
target="graph-n225"
Rscript --vanilla "${target}.r" "$font"
