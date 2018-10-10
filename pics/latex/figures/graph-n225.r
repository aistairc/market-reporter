require(ggplot2)
require(grid)
require(gridExtra)
require(scales)

args <- commandArgs(trailingOnly=T)

red <- "red"
black <- "#333333"
fontsize <- 24
fontsize.label <- 8
fontsize.spanlabel <- 7.5
ylim <- c(15750, 16120)

convd <- function(x) {
    ns <- as.integer(strsplit(as.character(x), "/")[[1]])
    d <- ns[2]
    m <- ns[1]
    y <- ns[3]
    return(sprintf("%04d-%02d-%02d", y, m, d))
}

today <- read.csv("_n225-2016-06-20.csv", header=F, sep=",")
breaktime <- rep(NA, 11)
skip <- length(breaktime)
values <- c(today[, 3][1:31],
            breaktime,
            today[, 3][32:62])

df <- data.frame(Time=1:length(values), Price=values)

g <- ggplot(df, aes(x=Time, y=Price)) +
    geom_line(size=1.1) +
    ylab("Nikkei 225 [JPY]") +
　　　　xlab("Time [JST]") +
    coord_cartesian(ylim=ylim) +
    scale_x_continuous(breaks=seq(1, 84, by=12),
                       labels=c("9:00",
                                "10:00",
                                "11:00",
                                "12:00",
                                "13:00",
                                "14:00",
                                "15:00"),
                       minor_breaks=NULL) +
    theme(text=element_text(size=fontsize),
          axis.text.x=element_text(size=fontsize, colour=black),
          axis.title.x=element_text(size=fontsize, margin=margin(15, 0, 0, 0)),
          axis.text.y=element_text(size=fontsize, colour=black),
          axis.title.y=element_text(size=fontsize, margin=margin(0, 15, 0, 0)),
          plot.title=element_text(hjust=0.5, margin=margin(0, 0, 15, 0)))

arrow.thickness <- 0.7
arrow.size <- unit(0.3, "cm")
arrow.y <- 16020

g <- g +
    geom_segment(aes(x=1, y=arrow.y, xend=31, yend=arrow.y),
                 colour=red,
                 size=arrow.thickness,
                 arrow=arrow(ends="both", length=arrow.size)) +
    geom_segment(aes(x=(31 +skip), y=arrow.y, xend=length(values), yend=arrow.y),
                 colour=red,
                 size=arrow.thickness,
                 arrow=arrow(ends="both", length=arrow.size))

    y <- 16050

    labelpoint <- data.frame(Time=16, Price=y)
    colnames(labelpoint) <- c("Time", "Price")
    g <- g +
        geom_text(data=labelpoint,
                  aes(x=Time, y=Price, label="2016-08-04 Morning"),
                  vjust=1,
                  size=fontsize.spanlabel)
    labelpoint <- data.frame(Time=((31 + skip + length(values))/2), Price=y)
    colnames(labelpoint) <- c("Time", "Price")
    g <- g +
        geom_text(data=labelpoint,
                  aes(x=Time, y=Price, label="2016-08-04 Afternoon"),
                  vjust=1,
                  size=fontsize.spanlabel)

cairo_pdf("graph-n225.pdf", width=12, family=args[1])
plot(g)
dev.off()
