suppressPackageStartupMessages({
  library(pscl)
  library(wnominate)
})
set.seed(20261006)
votes <- read.csv("model_matrix.csv", check.names = FALSE, na.strings = "")
matrix <- as.matrix(votes[, -1])
rownames(matrix) <- votes$legislator
matrix[matrix == 0] <- 6
matrix[is.na(matrix)] <- 9
rolls <- rollcall(matrix, yea = 1, nay = 6, missing = 9, notInLegis = 0,
                  legis.names = rownames(matrix), vote.names = colnames(matrix))
fit <- wnominate(rolls, dims = 2, minvotes = 20, lop = .025, trials = 3,
                 polarity = c("Michael Chippendale", "Kathleen A Fogarty"),
                 verbose = FALSE)
write.csv(fit$legislators[, c("coord1D", "coord2D")], "house-two-dimensional.csv")
print(fit$fits)
print(fit$legislators["Kathleen A Fogarty", c("coord1D", "coord2D")])
