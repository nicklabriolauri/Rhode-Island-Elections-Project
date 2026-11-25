library(pscl)
library(wnominate)
set.seed(20261006)
x <- read.csv("matrix.csv", row.names=1, check.names=FALSE)
m <- as.matrix(x)
rc <- rollcall(m, yea=1, nay=6, missing=9, notInLegis=0, legis.names=rownames(m), vote.names=colnames(m))
for (dims in c(1,2)) {
 set.seed(20261006)
 anchors <- c("Jessica de la Cruz","Dawn Euer")[seq_len(dims)]
 fit <- wnominate(rc,dims=dims,minvotes=20,lop=.025,trials=3,polarity=anchors,verbose=FALSE)
 write.csv(fit$legislators,sprintf("legislators-%s.csv",dims))
 write.csv(fit$rollcalls,sprintf("rollcalls-%s.csv",dims))
 print(fit)
 print(fit$legislators["Elaine J Morgan",])
 saveRDS(fit,sprintf("fit-%s.rds",dims))
}
